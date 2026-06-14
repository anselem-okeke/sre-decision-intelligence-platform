## Common Kubernetes Exit Codes


| Exit Code | Kubernetes Reason | Plain English Translation |
| :--- | :--- | :--- |
| **`137`** | `OOMKilled` or `SIGKILL` | **Out Of Memory.** The system killed the app because it tried to use more RAM than its defined Kubernetes limit, or the underlying node ran out of memory entirely. |
| **`139`** | `Segmentation Fault` | **Memory Bug.** The application tried to access a memory address it wasn't allowed to. This is usually a bug in the application code or a compiled binary library. |
| **`143`** | `SIGTERM` | **Graceful Shutdown.** Kubernetes asked the container to stop (e.g., during a deployment roll-out or scale-down), and the application closed down normally. |
| **`1`** | `Application Error` | **Generic Crash.** The application started, but crashed due to an internal error (like a missing configuration file, database connection failure, or syntax error). |
| **`125`** | `Docker/Containerd Fail` | **Runtime Failure.** The container runtime engine failed to run the command. The container itself didn't even get a chance to start. |
| **`126`** | `Command Invoke Error` | **Permission Denied.** The command or script specified in the container image cannot be executed, often due to wrong file permissions. |
| **`127`** | `File Not Found` | **Missing Binary.** The command or script path specified in your deployment configuration does not exist inside the container image. |


```bash
mkdir -p img

ffmpeg -i decision-intelligence-monitor.mp4 \
  -vf "fps=8,scale=720:-1:flags=lanczos" \
  -loop 0 img/decision-intelligence-monitor-small.gif
```