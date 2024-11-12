import asyncio
import os
from pathlib import Path

exit()
current_job = 0
scripts = list(Path("./jobs/").iterdir())
nextjob = 0

async def async_main():
    await asyncio.gather(*[async_thread(i) for i in range(0, 20)])

async def async_thread(threadId: int):
    global nextjob
    while nextjob < len(scripts):
        jobPath = scripts[nextjob]
        jobName = jobPath.stem
        print(f"{nextjob}/{len(scripts)}\t WC {int(((len(scripts)-nextjob) * 60 * 16)/20)} seconds\t{threadId} # {jobName}")
        nextjob += 1
        outFile = open(f"out/{jobName}.out", "w")
        errFile = open(f"out/{jobName}.err", "w")
        proc = await asyncio.create_subprocess_exec("/bin/bash", str(jobPath.absolute()), stdout=outFile, stderr=errFile)
        await proc.communicate()
        outFile.close()
        errFile.close()

asyncio.run(async_main())