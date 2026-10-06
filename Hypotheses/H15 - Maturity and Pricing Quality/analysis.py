"""H15: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import maturity_quality


def analyze(panel, config, options):
    return maturity_quality(options)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H15", *sys.argv[1:]])
