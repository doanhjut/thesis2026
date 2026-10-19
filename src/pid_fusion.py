"""
PID Adaptive Fusion
===================
Dong gop loi #1 — Luan van Thac si
"Phat hien Ransomware bang XAI va Active Learning"

Dung hop diem tinh (P_static, LightGBM/EMBER) va diem dong
(P_dynamic, Honeypot/Sandbox) bang bo dieu khien PID.

    e(t) = P_static - P_dynamic
    I[k] = clip(I[k-1] + e[k]*Delta-t[k], I_min, I_max)
    D[k] = (e[k]-e[k-1]) / Delta-t[k]
    u[k] = Kp*e[k] + Ki*I[k] + Kd*D[k]
    w_static = clip(sigmoid(u(t)), 0.1, 0.9)
    P_fused  = w_static * P_static + (1 - w_static) * P_dynamic

He so mac dinh tham chieu: Kp=0.85, Ki=0.12, Kd=0.35.
Day la heuristic dung hop theo lich su bat dong diem, khong phai chung minh
on dinh dieu khien cua mot plant vat ly. Hieu qua va do tre phai duoc do.
"""

from __future__ import annotations

import numpy as np

DEFAULT_KP = 0.85
DEFAULT_KI = 0.12
DEFAULT_KD = 0.35


class PIDController:
    """Bo dieu khien PID cho co che Adaptive Fusion.

    Dieu chinh trong so nhanh Static (LightGBM) dua tren sai so giua
    diem Static va diem Dynamic (Honeypot). Chi cap nhat khi ca hai diem
    da san sang; khong thay the thoi gian thu thap tin hieu dong.
    """

    def __init__(
        self,
        kp: float = DEFAULT_KP,
        ki: float = DEFAULT_KI,
        kd: float = DEFAULT_KD,
        setpoint: float = 0.0,
        integral_limits: tuple[float, float] = (-5.0, 5.0),
    ):
        if not np.isfinite([kp, ki, kd, setpoint, *integral_limits]).all():
            raise ValueError("PID coefficients must be finite.")
        if integral_limits[0] >= integral_limits[1]:
            raise ValueError("PID integral limits must be strictly increasing.")
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral_limits = (float(integral_limits[0]), float(integral_limits[1]))
        self.prev_error = None
        self.integral = 0.0
        self.last_terms = {'error': 0.0, 'integral': 0.0, 'derivative': 0.0, 'control': 0.0}

    def reset(self) -> None:
        """Xoa trang thai tich phan va sai so truoc do."""
        self.prev_error = None
        self.integral = 0.0
        self.last_terms = {'error': 0.0, 'integral': 0.0, 'derivative': 0.0, 'control': 0.0}

    def update(self, error: float, delta_t: float = 1.0) -> float:
        """Update with an elapsed interval; return w_static in [0.1, 0.9].

        The caller supplies the discrepancy and the configured setpoint is subtracted.
        Reset explicitly between independent sequences. Integral clipping is the
        anti-windup policy. The first derivative is zero because no previous
        observation exists.
        """
        if not np.isfinite([error, delta_t]).all() or delta_t <= 0:
            raise ValueError("PID error must be finite and delta_t must be positive.")
        effective_error = float(error) - self.setpoint
        integral = np.clip(
            self.integral + effective_error * float(delta_t),
            self.integral_limits[0], self.integral_limits[1],
        )
        derivative = (0.0 if self.prev_error is None else
                      (effective_error - self.prev_error) / float(delta_t))
        control = self.kp * effective_error + self.ki * integral + self.kd * derivative
        if not np.isfinite([integral, control]).all():
            raise ValueError("PID state overflow despite the configured reset and anti-windup policy.")
        self.integral = integral
        self.prev_error = effective_error
        self.last_terms = {'error': effective_error, 'integral': float(integral),
                           'derivative': float(derivative), 'control': float(control)}
        if control >= 0:
            w_static = 1.0 / (1.0 + np.exp(-control))
        else:
            exp_control = np.exp(control)
            w_static = exp_control / (1.0 + exp_control)
        return float(np.clip(w_static, 0.1, 0.9))


def fuse_scores(p_static: float, p_dynamic: float, w_static: float) -> float:
    """Dung hop hai xac suat. w_dynamic = 1 - w_static."""
    if not np.isfinite([p_static, p_dynamic, w_static]).all():
        raise ValueError("Fusion inputs must be finite.")
    if not 0 <= p_static <= 1 or not 0 <= p_dynamic <= 1:
        raise ValueError("Fusion input scores must be in [0, 1].")
    w_static = float(np.clip(w_static, 0.0, 1.0))
    return float(w_static * p_static + (1.0 - w_static) * p_dynamic)
