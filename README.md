<p align="center">
  <img style="width: auto; max-width: 50%; height: auto;" alt="Tino Wizard logo" src="Tino Wizard.png">
</p>

<h2 align="center">Tino Wizard</h2>
<h3 align="center"><em>The Installer Creator for Linux</em></h3>

**Tino Wizard** is the GUI developer tool in the **Tino Setup** suite. It allows developers to configure project settings, add files, setup shortcuts, and compile a single-file, one-click graphical installer.

---

### ✨ Features
- **Project Editor**: Save and load installation project configurations (`.tino` files).
- **Metadata Management**: Configure app name, version, publisher, websites, and custom licenses.
- **File & Directory Bundling**: Easily select files and directories to package.
- **Desktop Entry Integration**: Configure desktop shortcut properties (category, executable, icon).
- **One-Click Build**: Automatically packages your installer logic, application payload, and icon into a single executable.

---

### 🚀 Getting Started

#### 1. Download Tino Wizard
You can download the latest version from my site or GitHub release:
```
https://tmotagam.github.io/pages/Tino%20Setup/

https://github.com/Tino-Setup/Tino-Wizard/releases
```

#### 2. Install Tino Wizard
Install the wizard using the executable installer:
```bash
./TinoWizard
```

#### 3. Run Tino Wizard
Click on the icon or through command line
```bash
TinoWizard
```


#### 4. Building an Installer
1. Click **New Project** or load an existing `.tino` project.
2. Enter your application details.
3. Define your custom license and welcome text.
4. Add files and specify their installation target directories.
5. Click **Build Installer** to generate your standalone installer executable.

---

### 🛠️ Technology Stack
- **Python 3** & **Tkinter** (Developer UI)
- **PyInstaller** (To package the builder and installer engines)
- **lzma/tarfile** (For payload compression)

---

### 🧩 Contributing

Pull requests and Issues are welcome. For major changes, please open an issue first to discuss what you would like to change.

### 📄 License

**[GNU GPL 3.0](https://www.gnu.org/licenses/gpl-3.0.en.html)**
