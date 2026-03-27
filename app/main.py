import hydra
import os
from omegaconf import DictConfig
from internal.infrastructure.tui import run_tui

# Fix for macOS/Textual threading issues with HuggingFace tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

@hydra.main(version_base="1.3", config_path="../conf", config_name="config")
def main(cfg: DictConfig):
    """Boot layer entrypoint wrapped by Hydra."""
    run_tui(cfg)


if __name__ == "__main__":
    main()

