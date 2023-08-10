# MFCScript
Python CLI to check the availability of cars in the  Audi MFC pool.

# Setup
This is a Python3 Skript built on the curses and requests packages. Depending on your OS you might need to additionally install them.
```
# Windows example
pip install windows-curses
pip install requests
```
You can then run the script supplying your AudiMyNet username and password. If you're running this from inside a network you might need to supply a proxy address.
```
python main.py -u <AudiMyNetUser> -p <AudiMyNetPassword> --proxy 127.0.0.1:9000
```
