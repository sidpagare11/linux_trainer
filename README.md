This guide explains how to take the Python version of the Linux Terminal Lab, turn it into a completely standalone Windows application, and make it available to employees through Confluence.

The final user experience will be:

Confluence → Download → Double-click → Linux Terminal Lab opens

The employee will not need:

Python
VS Code
GitHub
PowerShell
A code editor
Access to your source code

GitHub is only used by you to store and maintain the source code.

1. Final Setup

The overall process is:

Python source code
        ↓
GitHub
        ↓
Build on a Windows computer
        ↓
Lockheed Linux Terminal Lab.exe
        ↓
Upload .exe or .zip to Confluence
        ↓
Employee downloads it
        ↓
Employee double-clicks it
        ↓
Trainer runs locally

Once the .exe is built, it operates independently of GitHub.

2. What You Need

You only need these items on the Windows computer that will be used to build the application:

Windows 10 or Windows 11
Your Linux Terminal Lab .py file
Python 3
PyInstaller

The employees using the finished application do not need any of these development tools.

3. Build the Application on Windows

The Windows executable must be built on a Windows computer.

Do not build the .exe on your Mac.

You can develop the application on macOS, but copy the final Python file to a Windows computer before creating the Windows executable.

Your source file should look something like:

Lockheed_Linux_Terminal_Lab_V4.py
4. Install Python on the Windows Build Computer

Go to the official Python website and install Python 3 for Windows.

During installation, make sure the option similar to:

Add Python to PATH

is enabled.

After installation, open PowerShell.

You can find PowerShell by searching:

PowerShell

from the Windows Start menu.

Run:

python --version

You should see something similar to:

Python 3.13.5

If python does not work, try:

py --version

If either one shows a Python version, you are ready.

5. Get Your Linux Trainer Code onto Windows

There are two simple options.

Option 1 — Download it from your GitHub

Go to your GitHub repository.

Click:

Code

Then:

Download ZIP

Extract the ZIP file somewhere easy to find.

For example:

Desktop\Linux-Terminal-Lab
Option 2 — Copy the Python File Directly

You can also simply move:

Lockheed_Linux_Terminal_Lab_V4.py

onto the Windows computer using a USB drive, OneDrive, approved internal storage, etc.

GitHub is not required for the build itself.

6. Test the Python Version First

Before creating the executable, make sure the trainer works normally.

Open the folder containing:

Lockheed_Linux_Terminal_Lab_V4.py

Click the File Explorer address bar.

Type:

powershell

and press Enter.

PowerShell should open directly inside that folder.

Run:

python Lockheed_Linux_Terminal_Lab_V4.py

If your computer uses the py command instead:

py Lockheed_Linux_Terminal_Lab_V4.py

The Linux Terminal Lab should open.

Test a few commands:

pwd
ls
ls -ltr

Make sure the interface looks correct.

Then close the trainer.

7. Install PyInstaller

PyInstaller turns the Python program into a Windows .exe.

Inside PowerShell, run:

python -m pip install pyinstaller

Or, if your computer uses py:

py -m pip install pyinstaller

Wait for installation to finish.

Then test it:

python -m PyInstaller --version

or:

py -m PyInstaller --version

You should see a version number.

8. Build a Test Version First

Before creating the final single-file application, create a test build.

Run:

python -m PyInstaller --noconfirm --clean --windowed --onedir --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V4.py

If you use py:

py -m PyInstaller --noconfirm --clean --windowed --onedir --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V4.py

PyInstaller will create several new files and folders.

You will now have:

build\
dist\
Lockheed Linux Terminal Lab.spec

Open:

dist

Then open:

Lockheed Linux Terminal Lab

Inside will be:

Lockheed Linux Terminal Lab.exe

Double-click it.

The application should open normally.

No PowerShell or Command Prompt window should appear behind it.

9. Fully Test the Packaged Application

Before creating the final version, test the important features.

Test navigation

Try:

pwd
ls
ls -l
ls -a
ls -ltr
cd
cd ..
Test file creation

Try:

mkdir test
touch test.txt
Test file management

Try commands such as:

cp
mv
rm

using the files available inside the training environment.

Test file reading

Try:

cat
head
tail
Test searching

Try:

grep
find
Test shell features

Test:

|
>
>>
&&

Also test:

Up-arrow command history
Down-arrow command history
Tab completion
Environment variables
Test the editor

Open a training file using:

vi filename

or:

nano filename

Edit the file.

Save it.

Then check the file using:

cat filename

Make sure the changes actually appear.

Test the training interface

Confirm that:

Current Lesson displays correctly
Course Map displays correctly
Lessons advance correctly
Hints work
Command Guide works
Scrollbars look correct
There are no white borders around the terminal
Reset Lab works
Files reset correctly
The application does not crash
10. Create the Final Standalone EXE

Once the test version works, build the final version.

Run:

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V4.py

Or:

py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V4.py

Wait for it to finish.

Open:

dist

You should now see:

Lockheed Linux Terminal Lab.exe

This is your final application.

11. Test That It Is Actually Independent

This is an important step.

Copy:

Lockheed Linux Terminal Lab.exe

out of the dist folder.

For example, place it on your Desktop.

Then double-click it.

It should still open.

The program should not require:

The original .py file
GitHub
Your project folder
VS Code
PyInstaller

For an even better test, copy the .exe onto a different Windows computer that does not have Python installed.

Launch it there.

If it works, you have confirmed that the application is standalone.

12. Optional — Add a Proper Application Icon

If you want the program to look more professional, create a Windows .ico file.

For example:

linux_trainer.ico

Put it inside:

assets\

Your project could look like:

Linux-Terminal-Lab\
│
├── Lockheed_Linux_Terminal_Lab_V4.py
│
└── assets\
    └── linux_trainer.ico

Then build using:

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Lockheed Linux Terminal Lab" --icon "assets\linux_trainer.ico" Lockheed_Linux_Terminal_Lab_V4.py

Your executable will then display the custom icon.

13. Prepare the File for Confluence

You now have:

Lockheed Linux Terminal Lab.exe

There are two ways you can distribute it.

Preferred Option

Upload the executable directly:

Lockheed Linux Terminal Lab.exe

This provides the simplest employee experience.

Alternative Option

If Confluence or company security does not permit direct .exe attachments, put it inside a ZIP file.

Create:

Lockheed_Linux_Terminal_Lab.zip

Inside:

Lockheed Linux Terminal Lab.exe

Employees would then:

Download ZIP
→ Extract ZIP
→ Double-click EXE
14. Upload the Trainer to Confluence

Go to the Confluence page where you want the trainer available.

You might create a page called:

Linux Terminal Training

Attach either:

Lockheed Linux Terminal Lab.exe

or:

Lockheed_Linux_Terminal_Lab.zip

The exact attachment controls may differ depending on the company's Confluence setup.

Once the file is attached, create a clear link or button on the page.

For example:

Download Linux Terminal Lab for Windows

Link that text to the attached file.

The employee should not need to know anything about GitHub or Python.

15. Recommended Confluence Page

The Confluence page can be extremely simple.

Linux Terminal Training Lab

The Linux Terminal Training Lab provides a safe environment for learning and practicing common Linux commands.

How to Start

1. Download the trainer

Click:

Download Linux Terminal Lab for Windows

2. Open the application

Open your Downloads folder and double-click:

Lockheed Linux Terminal Lab.exe

3. Begin training

Follow the Current Lesson shown on the right side of the application.

No installation or programming environment is required.

16. GitHub Is Not Needed by Employees

Your GitHub repository should contain things such as:

Lockheed_Linux_Terminal_Lab_V4.py
README.md
WINDOWS_BUILD_GUIDE.md

That repository is for:

Source control
Development
Future changes
Backup
Documentation

The employees using the trainer do not interact with GitHub.

The production flow is:

GitHub
   ↓
Developer
   ↓
Build EXE
   ↓
Confluence
   ↓
Employee

Not:

Confluence
   ↓
GitHub
   ↓
Python

The executable is completely separate once it has been built.

17. When You Update the Trainer

Suppose you later create:

Lockheed_Linux_Terminal_Lab_V5.py

You would repeat the build process.

Test:

python Lockheed_Linux_Terminal_Lab_V5.py

Then build:

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V5.py

You will receive a new:

Lockheed Linux Terminal Lab.exe

Test it.

Then replace the previous Confluence attachment with the updated version.

Employees do not need to know that the underlying Python source changed.

18. Recommended Versioning

Inside the application itself, continue displaying versions such as:

V4
V5
V6

You can also version the Confluence attachment:

Linux_Terminal_Lab_V4.zip

However, keep the application name itself simple:

Lockheed Linux Terminal Lab.exe

This gives users a consistent application name while still allowing you to track releases.

19. Important Corporate Security Consideration

Before making the application available to a large number of employees, test it on the actual company Windows environment.

Company-managed systems may use tools such as:

Microsoft Defender
SmartScreen
Application allow-listing
Endpoint security
Software restriction policies

A newly created unsigned executable may be blocked even if the program itself is safe.

If this happens, do not instruct employees to disable or bypass security controls.

Instead, work with the appropriate internal IT or security team.

They may want to:

Scan the executable
Review the source code
Code-sign the application
Allow-list the application
Host it through an approved software repository
Approve the Confluence attachment

For an internal training application, this is the correct long-term approach.

20. Recommended Final Test Before Uploading

Before placing a new version on Confluence, complete this checklist.

Application was built on Windows.

Python source version works correctly.

PyInstaller build completes successfully.

Final build uses --onefile.

Final build uses --windowed.

EXE launches by double-clicking.

No console window appears.

Application launches without GitHub.

Application launches without the .py file.

Test on another Windows computer if possible.

pwd works.

ls works.

ls -ltr works.

cd works.

mkdir works.

touch works.

cp works.

mv works.

rm works.

cat works.

grep works.

find works.

Pipes work.

Redirection works.

Tab completion works.

Command history works.

File editing works.

File saving works.

Lessons advance correctly.

Course Map follows progression.

Hint works.

Command Guide works.

Reset Lab works.

Terminal has no unwanted white border.

Scrollbars display correctly.

Application passes company security requirements.

Final EXE or ZIP uploaded to Confluence.

Confluence download link tested.

Short Version

Once everything is configured, your normal update process becomes very simple.

On your Windows build computer:
python Lockheed_Linux_Terminal_Lab_V4.py

Test it.

Then:

python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Lockheed Linux Terminal Lab" Lockheed_Linux_Terminal_Lab_V4.py

Take:

dist\Lockheed Linux Terminal Lab.exe

Upload it to Confluence.

The employee then does only:

Open Confluence
↓
Click Download Linux Terminal Lab
↓
Double-click Lockheed Linux Terminal Lab.exe
↓
Begin training

No GitHub, Python, code editor, or development environment is required for the employee.
