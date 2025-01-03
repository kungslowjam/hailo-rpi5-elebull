# Integration with Flet UI
This repository contains examples of basic pipelines using Hailo's H8 and H8L accelerators + Flet UI 

## Installation
### Clone the Repository
```bash
git clone https://github.com/kungslowjam/hailo-rpi5-elebull.git
```
Navigate to the repository directory:
```bash
cd hailo-rpi5-examples
```

### Quick Installation and RUN
Run the following script to automate the installation process:
```bash
./install.sh
```
```bash
    source setup_env.sh
```
Run example using USB camera - Use the device found by the previous script:

```bash
  python basic_pipelines/detection.py --input /dev/video0 
```
Run example using USB camera and Flet UI
```bash
flet run app.py
```
