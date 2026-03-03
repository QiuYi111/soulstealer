import hydra
from omegaconf import DictConfig
from internal.infrastructure.tui import run_tui

@hydra.main(version_base="1.3", config_path="../conf", config_name="config")
def main(cfg: DictConfig):
    """Boot layer entrypoint wrapped by Hydra."""
    run_tui(cfg)


if __name__ == "__main__":
    main()

