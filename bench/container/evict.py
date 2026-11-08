"""Drop every clean file page from the page cache, so the agent starts cold."""

import os

for root, dirs, files in os.walk("/"):
    if root.split("/")[1:2] in (["proc"], ["sys"], ["dev"]):
        dirs[:] = []
        continue
    for name in files:
        try:
            fd = os.open(os.path.join(root, name), os.O_RDONLY)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            os.close(fd)
        except OSError:
            pass
