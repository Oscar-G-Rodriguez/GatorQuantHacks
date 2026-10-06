"""H13: owns the scheduled exploratory study under its committed plan."""
from discovery.connections import option_relationships


def analyze(panel, config, options):
    return option_relationships(options)


if __name__ == "__main__":
    import sys
    from discovery.connections import main
    main(["task", "--study", "H13", *sys.argv[1:]])
