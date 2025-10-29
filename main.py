# coding=utf-8
"""
Main Execution File
"""

from config import setup_novel
from pipeline import NovelPipeline


def main():
    """Main execution function"""
    # Load configurations
    setup, config = setup_novel()

    # Run pipeline
    pipeline = NovelPipeline(
        setup=setup,
        config=config,
        state_file="novel_state_7.json",
        output_file="History_3.txt"
    )

    pipeline.run()


if __name__ == "__main__":
    main()