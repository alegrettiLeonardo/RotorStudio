"""Compare two independent ROSS runs; never updates either reference bundle."""
import argparse
from pathlib import Path
from infrastructure import compare, verified_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--rtol", type=float, default=2e-12)
    parser.add_argument("--atol", type=float, default=1e-12)
    args = parser.parse_args()
    error = compare(verified_bundle(args.reference), verified_bundle(args.actual),
                    rtol=args.rtol, atol=args.atol)
    print(f"ROSS-to-ROSS reproducibility passed; max absolute error={error:.6g}; NOT Fortran parity")


if __name__ == "__main__":
    main()
