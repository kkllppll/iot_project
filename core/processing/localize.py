import numpy as np

SPEED_OF_SOUND = 343.0  # m/s

def predict_tdoa(point, mic_a, mic_b):
    pa = np.array(point)
    a = np.array(mic_a)
    b = np.array(mic_b)
    da = np.linalg.norm(pa - a)
    db = np.linalg.norm(pa - b)
    return (db - da) / SPEED_OF_SOUND

def localize_grid(room_w, room_h, mic_positions, tdoa_pairs, step=0.1):
    """
    mic_positions: dict {mic_id: (x,y)}
    tdoa_pairs: list of tuples (mic_a_id, mic_b_id, measured_tau)
    """
    xs = np.arange(0.0, room_w + 1e-9, step)
    ys = np.arange(0.0, room_h + 1e-9, step)

    best = None
    best_err = float("inf")

    for x in xs:
        for y in ys:
            err = 0.0
            for a_id, b_id, tau in tdoa_pairs:
                pred = predict_tdoa((x, y), mic_positions[a_id], mic_positions[b_id])
                d = (pred - tau)
                err += d * d
            if err < best_err:
                best_err = err
                best = (x, y)

    return best, float(best_err)




def crop_around_peak(x, sr, window_sec=0.5, ignore_edge_sec=0.3):
    n = len(x)
    a0 = int(ignore_edge_sec * sr)
    b0 = n - int(ignore_edge_sec * sr)

    # якщо аудіо надто коротке нічого не ріжемо
    if b0 <= a0 + 100:
        return x

    mid = x[a0:b0]
    peak = int(np.argmax(mid * mid)) + a0

    w = int(window_sec * sr)
    start = max(0, peak - w)
    end = min(n, peak + w)
    return x[start:end]