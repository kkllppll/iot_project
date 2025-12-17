import numpy as np

def gcc_phat(sig, refsig, fs, max_tau=None, interp=16):
    n = sig.shape[0] + refsig.shape[0]

    SIG = np.fft.rfft(sig, n=n)
    REFSIG = np.fft.rfft(refsig, n=n)
    R = SIG * np.conj(REFSIG)

    denom = np.abs(R)
    denom[denom < 1e-12] = 1e-12
    R /= denom

    cc = np.fft.irfft(R, n=(interp * n))

    max_shift = int(interp * n / 2)
    if max_tau is not None:
        max_shift = min(int(interp * fs * max_tau), max_shift)

    cc = np.concatenate((cc[-max_shift:], cc[:max_shift+1]))
    shift = np.argmax(np.abs(cc)) - max_shift

    tau = shift / float(interp * fs)
    return tau
