from src.utilities.logger import Logger
from src.configuration import Configuration
from dotenv import load_dotenv
from src.execution_orchestrator import ExecutionOrchestrator


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    trading_system = ExecutionOrchestrator(cfg)
    trading_system.start()
