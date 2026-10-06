import os

# One numerical thread per process prevents workers multiplying BLAS threads.
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
