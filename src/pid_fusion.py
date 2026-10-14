"""
PID Adaptive Fusion
===================
Dong gop loi #1 — Luan van Thac si
"Phat hien Ransomware bang XAI va Active Learning"

Dung hop diem tinh (P_static, LightGBM/EMBER) va diem dong
(P_dynamic, Honeypot/Sandbox) bang bo dieu khien PID.

    e(t) = P_static - P_dynamic
    u[k] = Kp*e[k] + Ki*sum(e[0:k+1]) + Kd*(e[k]-e[k-1])
    w_static = clip(sigmoid(u(t)), 0.1, 0.9)
    P_fused  = w_static * P_static + (1 - w_static) * P_dynamic

He so mac dinh tham chieu: Kp=0.85, Ki=0.12, Kd=0.35.
Day la cap nhat theo buoc, khong co Delta-t hoac anti-windup tich phan.
Hieu qua phan loai va do tre phai duoc do; khong duoc suy ra tu cong thuc.
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
    ):
        if not np.isfinite([kp, ki, kd, setpoint]).all():
            raise ValueError("PID coefficients must be finite.")
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0.0
        self.integral = 0.0

    def reset(self) -> None:
        """Xoa trang thai tich phan va sai so truoc do."""
        self.prev_error = 0.0
        self.integral = 0.0

    def update(self, error: float) -> float:
        """Update by observation step; return w_static in [0.1, 0.9].

        The caller supplies the error; setpoint is retained for API compatibility.
        Reset explicitly between independent sequences. No automatic state reset.
        """
        if not np.isfinite(error):
            raise ValueError("PID error must be finite.")
        integral = self.integral + error
        derivative = error - self.prev_error
        control = self.kp * error + self.ki * integral + self.kd * derivative
        if not np.isfinite([integral, control]).all():
            raise ValueError("PID state overflow; define a reset policy or evaluate anti-windup separately.")
        self.integral = integral
        self.prev_error = error
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
