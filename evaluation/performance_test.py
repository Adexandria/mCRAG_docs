import subprocess
import re

bash_path = r"C:\Program Files\Git\bin\bash.exe" 
total_runtime = 0
for i in range(10):
    print(f"Running performance test iteration {i + 1}")

    result = subprocess.run(
    [bash_path,'./run_pipeline.sh', 
     '--query', 'Which attempt gave the best result',
     '--experiment-id', '1',
     '--skip-testcases',
     '--skip-ingest',
     '--use-base-retriever'],
    capture_output=True,
    text=True,
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)

    match = re.search(r'RUNTIME=(\d+)s', result.stdout)
    if match:
        runtime_seconds = int(match.group(1))
        print(f"Pipeline {i + 1} took {runtime_seconds} seconds")
        total_runtime += runtime_seconds


print(f"Total runtime across all iterations: {total_runtime} seconds")
print(f"Average runtime per iteration: {total_runtime / 10} seconds")
