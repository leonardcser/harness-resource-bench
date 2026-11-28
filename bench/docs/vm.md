# The benchmark VM

A VM with 12 vCPUs on a Proxmox host with an AMD Ryzen 9 7900X (12 cores in two
CCDs, each with its own L3). The hook `proxmox/bench-isolate` runs when the VM
starts and stops. While the VM runs:

- **Reserved cores:** the VM owns the whole second CCD (host threads 6 to 11 and
  18 to 23). No other guest or host service runs there.
- **Own L3:** no other work shares that cache.
- **Pinning:** each vCPU runs on one host thread. Each pair 2k, 2k+1 is one
  physical core. QEMU's threads share the core of vCPUs 0 and 1, where the
  harness runs.
- **Fixed clock:** the reserved cores stay at 4.7 GHz, the base clock.
- **Interrupts:** hardware interrupts go to other host threads. NVMe queues fire
  there only for the VM's own I/O.
- **Updates:** off, so packages do not change between runs.
