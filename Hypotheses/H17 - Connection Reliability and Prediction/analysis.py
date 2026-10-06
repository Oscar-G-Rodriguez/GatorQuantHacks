"""H17: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import ridge_predictions


def analyze(panel, config, options):
    return ridge_predictions(panel, config, options)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H17", *sys.argv[1:]])
