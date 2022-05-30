from mininet.node import Docker
from mininet.log import info

from fogbed.emulation import EmulationCore
from fogbed.resources import NotEnoughResourcesAvailable, ResourceModel
from fogbed.resources.allocation import CPUAllocator, MemoryAllocator


class EdgeResourceModel(ResourceModel):
    def __init__(self, max_cu=32, max_mu=512) -> None:
        super().__init__(max_cu, max_mu)

        self.cpu_allocator = CPUAllocator(
            compute_single_cu=self.calculate_cpu_percentage)

        self.memory_allocator = MemoryAllocator(
            compute_single_mu=self.calculate_memory_percentage)


    def allocate_cpu(self, container: Docker):
        requested_cu = self.get_compute_units(container)
        
        if(requested_cu + self.allocated_cu > self.max_cu):
            raise NotEnoughResourcesAvailable('Not enough compute resources left.')
        
        self.allocated_cu += requested_cu
        cpu_period, cpu_quota = self.cpu_allocator.calculate(requested_cu)
        self.update_cpu_limit(container, cpu_period, cpu_quota)
    

    def free_cpu(self, container: Docker):
        requested_cu = self.get_compute_units(container)
        self.allocated_cu -= requested_cu


    def allocate_memory(self, container: Docker):
        requested_mu = self.get_memory_units(container)

        if(requested_mu + self.allocated_mu > self.max_mu):
            raise NotEnoughResourcesAvailable('Not enough compute resources left.')

        self.allocated_mu += requested_mu
        memory_limit = self.memory_allocator.calculate(requested_mu)
        container.updateMemoryLimit(mem_limit=memory_limit)


    def free_memory(self, container: Docker):
        pass

    def calculate_cpu_percentage(self) -> float:
        return EmulationCore.max_cpu() / EmulationCore.get_all_compute_units()

    def calculate_memory_percentage(self) -> float:
        return EmulationCore.max_memory() / EmulationCore.get_all_memory_units()
    



# ================================================================================== #
class CloudResourceModel(EdgeResourceModel):
    def __init__(self, max_cu=32, max_mu=1024) -> None:
        super().__init__(max_cu, max_mu)

        self.cpu = CPUAllocator(
            compute_single_cu=self.calculate_cpu_percentage
        )

    def allocate_cpu(self, container: Docker):
        requested_cu = self.get_compute_units(container)
        self.allocated_cu += requested_cu
        self._update_all_containers()

    def free_cpu(self, container: Docker):
        requested_cu = self.get_compute_units(container)
        self.allocated_cu -= requested_cu
        self._update_all_containers()


    def allocate_memory(self, container: Docker):
        pass

    def free_memory(self, container: Docker):
        pass

    
    def calculate_cpu_percentage(self) -> float:
        e_cpu = EmulationCore.max_cpu()
        all_compute_units = EmulationCore.get_all_compute_units()
        cpu_op_factor = self._cpu_over_provisioning_factor()
        return (e_cpu / all_compute_units) * cpu_op_factor

    def _cpu_over_provisioning_factor(self) -> float:
        return float(self.max_cu) / max(self.max_cu, self.allocated_cu)
    

    def _update_all_containers(self):
        info('\n*** Updating all containers\n')

        for container in self.allocated_containers:
            requested_cu = self.get_compute_units(container)
            cpu_period, cpu_quota = self.cpu.calculate(requested_cu)
            self.update_cpu_limit(container, cpu_period, cpu_quota)