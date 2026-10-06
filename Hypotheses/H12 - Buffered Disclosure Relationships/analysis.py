"""H12: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import dense_relationships


def analyze(panel, config, options):
    return dense_relationships(panel, config)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H12", *sys.argv[1:]])
