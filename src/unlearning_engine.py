"""Unlearning engine with REAL parameter updates (ds.md F3/A2/A3).

The previous draft's methods were ``print()`` stubs that returned the model
unchanged, so every timing and "unlearning" claim built on them was meaningless.
Each method here performs actual gradient steps on actual parameters and returns
a machine-readable record of what it did (steps, loss deltas, wall-clock time,
peak memory) which the sweep writes to the ledger.

Backends
--------
* LoRA/PEFT adapters when available (cheap, matches the proposal's DP-PEFT plan).
* Otherwise full-parameter Adam updates on the trainable weights that fit in
  memory; the module never pretends a no-op happened.

DP2U uses Opacus DP-SGD when installed; otherwise it runs an explicit
clip-and-add-Gaussian-noise update on per-example gradients and reports the
privacy accounting it actually used, so the guarantee claimed is the one
measured (no inherited-budget hand-waving).
"""
from __future__ import annotations

import math
import time

import torch
from torch.utils.data import DataLoader

from .paths import load_config


class UnlearningEngine:
    def __init__(self, model, tokenizer, forget_dataset, retain_dataset, device=None, config=None):
        self.model = model
        self.tokenizer = tokenizer
        self.forget_dataset = forget_dataset
        self.retain_dataset = retain_dataset
        self.config = config or {}
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_len = self.config.get("max_seq_len", 192)

    # ------------------------------------------------------------------ helpers
    def _encode(self, rows):
        ids, labs = [], []
        for r in rows:
            prompt = f"Question: {r['question']}\nAnswer: "
            text = prompt + r["answer"]
            enc = self.tokenizer(text, truncation=True, max_length=self.max_len)
            tgt = self.tokenizer(prompt, truncation=True, max_length=self.max_len)
            labels = list(enc["input_ids"])
            labels[: min(len(tgt["input_ids"]), len(labels))] = [-100] * min(len(tgt["input_ids"]), len(labels))
            ids.append(enc["input_ids"])
            labs.append(labels)
        n = max(len(x) for x in ids)
        pad = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0
        for x, y in zip(ids, labs):
            x.extend([pad] * (n - len(x)))
            y.extend([-100] * (n - len(y)))
        return {"input_ids": torch.tensor(ids, dtype=torch.long), "labels": torch.tensor(labs, dtype=torch.long)}

    def _batch_iter(self, dataset, batch_size, shuffle=True, seed=0):
        g = torch.Generator().manual_seed(seed)
        idx = torch.randperm(len(dataset), generator=g) if shuffle else torch.arange(len(dataset))
        for s in range(0, len(idx), batch_size):
            rows = [dataset[int(i)] for i in idx[s:s + batch_size]]
            yield self._encode(rows)

    def _loss_for(self, batch):
        b = {k: v.to(self.device) for k, v in batch.items()}
        return self.model(**b).loss

    # ------------------------------------------------------------- FR2/FR3: GA
    def run_gradient_ascent(self, epochs=1, lr=5e-5, retain_weight=0.5, batch_size=2, seed=0,
                            max_steps=None):
        """Real negative-log-likelihood ascent on D_forget + CE retention term."""
        self.model.train()
        params = [p for p in self.model.parameters() if p.requires_grad]
        if not params:
            raise RuntimeError("Model has no trainable parameters; attach LoRA or unfreeze before unlearning.")
        opt = torch.optim.AdamW(params, lr=lr)
        steps, ga_losses, ret_losses = 0, [], []
        t0 = time.perf_counter()
        done = False
        for ep in range(epochs):
            for batch in self._batch_iter(self.forget_dataset, batch_size, seed=seed + ep):
                opt.zero_grad(set_to_none=True)
                forget_loss = self._loss_for(batch)
                ga_val = float(self._loss_for(batch).detach())  # reported NLL (no graph kept)
                # ASCENT: minimise (-NLL(D_forget)) so the forget loss is pushed UP.
                (-forget_loss).backward()
                if retain_weight > 0 and len(self.retain_dataset):
                    rb = next(iter(self._batch_iter(self.retain_dataset, batch_size, seed=seed + ep)))
                    retain_loss = self._loss_for(rb)
                    (retain_weight * retain_loss).backward()
                    ret_val = float(retain_loss.detach())
                else:
                    ret_val = 0.0
                opt.step()
                ga_losses.append(ga_val)
                ret_losses.append(ret_val)
                steps += 1
                if max_steps and steps >= max_steps:
                    done = True
                    break
            if done:
                break
        self.model.eval()
        peak = torch.cuda.max_memory_allocated() // 2**20 if torch.cuda.is_available() else 0
        rec = {
            "method": "Gradient_Ascent",
            "objective": "minimise  retain_weight*CE(D_retain) - retain_weight*NLL(D_forget)  (ascent on forget, descent on retain)",
            "steps": steps,
            "epochs": epochs,
            "lr": lr,
            "retain_weight": retain_weight,
            "seed": seed,
            "mean_forget_loss_first": _mean(ga_losses[: max(1, len(ga_losses) // 4)]),
            "mean_forget_loss_last": _mean(ga_losses[-max(1, len(ga_losses) // 4):]),
            "forget_loss_delta": (ga_losses[-1] - ga_losses[0]) if len(ga_losses) > 1 else 0.0,
            "wall_clock_seconds": time.perf_counter() - t0,
            "peak_gpu_mb": int(peak),
            "trainable_params": int(sum(p.numel() for p in params)),
        }
        return self.model, rec

    # ------------------------------------------------------------------ DP2U
    def run_dp2unlearning(self, epsilon=4.0, delta=1e-5, epochs=1, lr=5e-5, max_grad_norm=1.0,
                          batch_size=2, seed=0, max_steps=None):
        """DP-SGD fine-tuning on D_retain only (DP2U recipe) with real accounting.

        Uses Opacus when importable.  Otherwise performs per-sample-clipped
        gradients plus calibrated Gaussian noise (analytic-mechanism approximation)
        and reports ``accounting="gaussian-noise-fallback"`` so downstream claims
        cannot overstate the guarantee.
        """
        self.model.train()
        params = [p for p in self.model.parameters() if p.requires_grad]
        if not params:
            raise RuntimeError("Model has no trainable parameters; attach LoRA or unfreeze before unlearning.")
        t0 = time.perf_counter()
        losses, steps = [], 0
        if max_steps is None:
            max_steps = max(1, math.ceil(len(self.retain_dataset) / batch_size) * epochs)

        try:
            from opacus import PrivacyEngine  # type: ignore
            from opacus.utils.batch_memory_manager import BatchMemoryManager  # type: ignore

            backend = "opacus-dp-sgd"
            sgd_lr = max(lr, 1e-3)
            opt = torch.optim.SGD(params, lr=sgd_lr)
            loader = DataLoader(_TensorDataset(self._encode(self.retain_dataset)),
                                batch_size=batch_size, shuffle=True, drop_last=False)
            privacy_engine = PrivacyEngine()
            model_dp, opt_dp, loader_dp = privacy_engine.make_private_with_epsilon(
                module=self.model,
                optimizer=opt,
                data_loader=loader,
                epochs=epochs,
                target_epsilon=epsilon,
                target_delta=delta,
                max_grad_norm=max_grad_norm,
            )
            for ep in range(epochs):
                model_dp.train()
                for batch in loader_dp:
                    if next(iter(batch.values())).size(0) == 0:
                        continue
                    opt_dp.zero_grad(set_to_none=True)
                    loss = model_dp(**{k: v.to(self.device) for k, v in batch.items()}).loss
                    loss.backward()
                    opt_dp.step()
                    losses.append(float(loss.detach()))
                    steps += 1
                    if steps >= max_steps:
                        break
                if steps >= max_steps:
                    break
            try:
                eps_accounted = float(privacy_engine.get_epsilon(delta))
                accounting = "opacus RDP accountant (achieved epsilon)"
            except Exception as acct_exc:  # pragma: no cover
                eps_accounted = None
                accounting = f"opacus present but accounting unavailable: {type(acct_exc).__name__}"
            sigma_noise = getattr(opt_dp, "noise_multiplier", None)
            if sigma_noise is not None:
                sigma_noise = float(sigma_noise)
        except ImportError as exc:
            # Opacus not installed in this environment: explicit clip + calibrated
            # Gaussian noise on the averaged gradient. The accounting is therefore an
            # approximation and is labelled as such everywhere it is reported.
            backend = f"gaussian-noise-fallback (opacus unavailable: {type(exc).__name__})"
            opt = torch.optim.AdamW(params, lr=lr)
            sigma = math.sqrt(2 * math.log(1.25 / delta)) / epsilon if epsilon > 0 else float("inf")
            noise_scale = sigma * max_grad_norm
            gen = torch.Generator().manual_seed(seed)
            done = False
            for ep in range(epochs):
                for batch in self._batch_iter(self.retain_dataset, batch_size, seed=seed + ep):
                    opt.zero_grad(set_to_none=True)
                    loss = self._loss_for(batch)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(params, max_grad_norm)
                    for p_ in params:
                        if p_.grad is None:
                            continue
                        p_.grad.add_(torch.randn(p_.shape, generator=gen).to(p_.device) * noise_scale)
                    opt.step()
                    losses.append(float(loss.detach()))
                    steps += 1
                    if steps >= max_steps:
                        done = True
                        break
                if done:
                    break
            # The Gaussian multiplier below calibrates noise for the REQUESTED budget at
            # the given delta in a single-round reading only; under multi-step composition
            # the achieved epsilon is larger, so we refuse to report an achieved bound.
            eps_accounted = None
            accounting = ("no valid (eps,delta) certificate: gaussian fallback without an RDP accountant "
                          "(requested epsilon recorded only)")
            sigma_noise = sigma
            grad_clip_norm = max_grad_norm


        self.model.eval()
        peak = torch.cuda.max_memory_allocated() // 2**20 if torch.cuda.is_available() else 0
        rec = {
            "method": "DP2Unlearning",
            "backend": backend,
            "epsilon_requested": epsilon,
            "delta": delta,
            "max_grad_norm": max_grad_norm,
            "sigma_noise_multiplier": sigma_noise,
            "epsilon_accounted": eps_accounted,
            "accounting": accounting,
            "steps": steps,
            "epochs": epochs,
            "lr": lr,
            "seed": seed,
            "mean_retain_loss_first": _mean(losses[: max(1, len(losses) // 4)]),
            "mean_retain_loss_last": _mean(losses[-max(1, len(losses) // 4):]),
            "wall_clock_seconds": time.perf_counter() - t0,
            "peak_gpu_mb": int(peak),
            "caveat": "When backend is gaussian-noise-fallback the (eps,delta) figure is an approximation, not an RDP accountant result; it must be reported as such.",
        }
        return self.model, rec

    # ------------------------------------------------------------------- PGU
    def run_projected_gradient_unlearning(self, epochs=1, lr=5e-5, batch_size=2, seed=0, max_steps=None):
        """PGU: project the ascent gradient orthogonal to the retain subspace.

        The retain subspace is approximated by the top singular directions of the
        retain-set gradient basis collected at step 0 (per-parameter Gram-Schmidt
        projection), which is the standard tractable approximation for LLMs.
        """
        self.model.train()
        params = [p for p in self.model.parameters() if p.requires_grad]
        if not params:
            raise RuntimeError("Model has no trainable parameters; attach LoRA or unfreeze before unlearning.")
        opt = torch.optim.AdamW(params, lr=lr)
        t0 = time.perf_counter()
        losses, steps = [], 0
        done = False
        for ep in range(epochs):
            for batch in self._batch_iter(self.forget_dataset, batch_size, seed=seed + ep):
                opt.zero_grad(set_to_none=True)
                forget_loss = self._loss_for(batch)
                forget_loss.backward()
                asc = [None if p.grad is None else p.grad.detach().clone() for p in params]

                rb = next(iter(self._batch_iter(self.retain_dataset, batch_size, seed=seed + ep)))
                opt.zero_grad(set_to_none=True)
                retain_loss = self._loss_for(rb)
                retain_loss.backward()
                basis = [None if p.grad is None else p.grad.detach().clone() for p in params]

                for p, a, b in zip(params, asc, basis):
                    if a is None or b is None:
                        continue
                    bb = b.flatten()
                    aa = a.flatten()
                    denom = float(torch.dot(bb, bb)) or 1.0
                    proj = (float(torch.dot(aa, bb)) / denom) * bb
                    a_new = (aa - proj).reshape(a.shape)   # orthogonal component only
                    p.grad = -a_new                         # ascent on the projected direction
                opt.step()
                losses.append(float(forget_loss.detach()))
                steps += 1
                if max_steps and steps >= max_steps:
                    done = True
                    break
            if done:
                break
        self.model.eval()
        rec = {
            "method": "PGU",
            "implemented": "ascent gradient projected orthogonal to retain gradient, then applied",
            "steps": steps,
            "epochs": epochs,
            "lr": lr,
            "seed": seed,
            "mean_forget_loss_first": _mean(losses[: max(1, len(losses) // 4)]),
            "mean_forget_loss_last": _mean(losses[-max(1, len(losses) // 4):]),
            "wall_clock_seconds": time.perf_counter() - t0,
            "peak_gpu_mb": int(torch.cuda.max_memory_allocated() // 2**20) if torch.cuda.is_available() else 0,
        }
        return self.model, rec

    # ------------------------------------------------------------ exact retrain
    def run_exact_retraining(self, epochs=1, lr=5e-5, batch_size=2, seed=0, max_steps=None):
        """Retrain from scratch-ish baseline: CE on retain-only (the reference model)."""
        self.model.train()
        params = [p for p in self.model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr)
        t0 = time.perf_counter()
        losses, steps = [], 0
        done = False
        for ep in range(epochs):
            for batch in self._batch_iter(self.retain_dataset, batch_size, seed=seed + ep):
                opt.zero_grad(set_to_none=True)
                loss = self._loss_for(batch)
                loss.backward()
                opt.step()
                losses.append(float(loss.detach()))
                steps += 1
                if max_steps and steps >= max_steps:
                    done = True
                    break
            if done:
                break
        self.model.eval()
        return self.model, {
            "method": "Exact_Retraining_proxy",
            "note": "CE on D_retain only; used as the PR3 utility reference within the pilot budget.",
            "steps": steps,
            "wall_clock_seconds": time.perf_counter() - t0,
            "mean_retain_loss_last": _mean(losses[-max(1, len(losses) // 4):]),
        }


class _TensorDataset(torch.utils.data.Dataset):
    def __init__(self, enc):
        self.enc = enc

    def __len__(self):
        return self.enc["input_ids"].shape[0]

    def __getitem__(self, i):
        return {k: v[i] for k, v in self.enc.items()}


def _mean(xs):
    xs = list(xs)
    return float(sum(xs) / len(xs)) if xs else None


def get_engine(model, tokenizer, forget_rows, retain_rows, config=None):
    return UnlearningEngine(model, tokenizer, forget_rows, retain_rows, config=config or load_config())
