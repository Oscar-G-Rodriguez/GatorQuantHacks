"""H14: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import option_repricing


def analyze(panel, config, options):
    return option_repricing(options)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H14", *sys.argv[1:]])
