# PointCloud Processor

An automated tool for processing, converting, and filtering 3D point clouds (supporting `.e57`, `.las`, `.ply`, etc.) powered by Open3D.

---

**Download & Getting Started**

1. Go to **Releases** (or the **Actions** tab) in this repository and download the latest `PointCloudProcessor.exe`.
2. Double-click the file to run it on any 64-bit Windows PC. 
3. A local Python installation is **not** required on the target PC.

---

**Windows Troubleshooting**

**1. Warning: "Windows protected your PC" (SmartScreen)**
* **Cause:** The application does not carry a paid Microsoft developer certificate.
* **Solution:** Click **"More info"** in the blue pop-up banner, then select **"Run anyway"**.

**2. Error: "MSVCP140.dll / VCRUNTIME140.dll missing"**
* **Cause:** Fresh Windows installations may lack the C++ runtime libraries required by Open3D.
* **Solution:** Download and install the free official **Visual C++ Redistributable (x64)** package from Microsoft:
  * Download: [aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

**3. Antivirus flag (False Positive)**
* **Cause:** Some antivirus tools flag self-extracting PyInstaller executables as suspicious because the Python runtime is bundled inside.
* **Solution:** Add the `.exe` file as an exception/exclusion in Windows Defender or your third-party antivirus software.

---

**Licenses & Third-Party Software**

This project uses Open3D for 3D point cloud processing.
* **Open3D:** MIT License (Copyright (c) 2018-2026 www.open3d.org)
