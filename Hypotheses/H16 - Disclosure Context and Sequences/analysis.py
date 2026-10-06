"""H16: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import context_interactions


def analyze(panel, config, options):
    return context_interactions(panel, config)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H16", *sys.argv[1:]])
