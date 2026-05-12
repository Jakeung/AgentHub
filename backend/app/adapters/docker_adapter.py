"""Docker adapter - wraps docker-py for container operations."""
import docker
from docker.errors import NotFound, APIError
import logging

logger = logging.getLogger(__name__)

_client = None


def get_docker_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


class DockerAdapter:
    def __init__(self):
        self.client = get_docker_client()

    def create_container(
        self,
        image: str,
        name: str,
        port: int,
        data_dir: str,
        mem_limit_mb: int,
        cpu_limit: float,
        environment: dict,
        api_server_key: str = "",
        llm_env: dict | None = None,
    ):
        """Create a container without starting it."""
        # Enable OpenAI-compatible API server inside the gateway
        env = dict(environment) if environment else {}
        env.setdefault("API_SERVER_ENABLED", "true")
        env.setdefault("API_SERVER_HOST", "0.0.0.0")
        env.setdefault("API_SERVER_PORT", "8642")
        env.setdefault("GATEWAY_ALLOW_ALL_USERS", "true")
        if api_server_key:
            env.setdefault("API_SERVER_KEY", api_server_key)
        if llm_env:
            env.update(llm_env)

        container = self.client.containers.create(
            image=image,
            name=name,
            command=["sh", "-c", "chown -R hermes:hermes /opt/data 2>/dev/null; exec gateway run"],
            ports={"8642/tcp": ("127.0.0.1", port)},
            volumes={
                data_dir: {"bind": "/opt/data", "mode": "rw"},
                "/etc/localtime": {"bind": "/etc/localtime", "mode": "ro"},
            },
            mem_limit=f"{mem_limit_mb}m",
            memswap_limit=f"{mem_limit_mb * 2}m",
            nano_cpus=int(cpu_limit * 1e9),
            pids_limit=256,
            environment=env,
            restart_policy={"Name": "unless-stopped"},
            network="agenthub-network",
            detach=True,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            cap_add=["NET_RAW", "SETUID", "SETGID", "CHOWN", "DAC_OVERRIDE"],
            tmpfs={"/tmp": "size=256m"},
        )
        return container.id

    def start_container(self, container_id: str):
        container = self.client.containers.get(container_id)
        container.start()

    def stop_container(self, container_id: str, timeout: int = 10):
        container = self.client.containers.get(container_id)
        container.stop(timeout=timeout)

    def restart_container(self, container_id: str, timeout: int = 10):
        container = self.client.containers.get(container_id)
        container.restart(timeout=timeout)

    def remove_container(self, container_id: str, force: bool = True):
        container = self.client.containers.get(container_id)
        container.remove(force=force)

    def get_container_status(self, container_id: str) -> str | None:
        try:
            container = self.client.containers.get(container_id)
            return container.status  # running, exited, created, etc.
        except NotFound:
            return None

    def get_container_stats(self, container_id: str) -> dict | None:
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            return self._parse_stats(stats)
        except (NotFound, APIError):
            return None

    def get_container_logs(self, container_id: str, tail: int = 100) -> list[str]:
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
            return logs.strip().split("\n") if logs.strip() else []
        except (NotFound, APIError):
            return []

    def container_exists(self, name: str) -> bool:
        try:
            self.client.containers.get(name)
            return True
        except NotFound:
            return False

    def exec_in_container(self, container_id: str, cmd: str) -> str:
        container = self.client.containers.get(container_id)
        result = container.exec_run(["sh", "-c", cmd])
        return result.output.decode("utf-8", errors="replace") if result.output else ""

    def get_used_host_ports(self) -> set[int]:
        """Get all host ports currently bound by Docker containers."""
        ports = set()
        try:
            for container in self.client.containers.list(all=True):
                for bindings in (container.ports or {}).values():
                    if bindings:
                        for b in bindings:
                            try:
                                ports.add(int(b["HostPort"]))
                            except (KeyError, ValueError):
                                pass
        except APIError:
            pass
        return ports

    def pull_image(self, image: str):
        """Pull (or update) a Docker image."""
        self.client.images.pull(image)

    def get_image_id(self, image: str) -> str | None:
        try:
            return self.client.images.get(image).id
        except (NotFound, APIError):
            return None

    def get_container_image_id(self, container_id: str) -> str | None:
        try:
            container = self.client.containers.get(container_id)
            return container.image.id
        except (NotFound, APIError):
            return None

    def load_image_from_tar(self, tar_path: str):
        with open(tar_path, "rb") as f:
            self.client.images.load(f)

    def _parse_stats(self, stats: dict) -> dict:
        """Parse docker stats into a simpler format."""
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                       stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)

        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)

        networks = stats.get("networks", {})
        rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
        tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_used_mb": mem_usage // (1024 * 1024),
            "memory_limit_mb": mem_limit // (1024 * 1024),
            "memory_percent": round(mem_usage / mem_limit * 100, 1) if mem_limit else 0,
            "network_rx_bytes": rx_bytes,
            "network_tx_bytes": tx_bytes,
        }
