# ILIAD

A simple and easy ilias downloader written with python. It helps you to download files on ilias to your computer.
The original Repository can be found at [iliaD](https://github.com/cold-soda-jay/iliaD) 


![Title](https://github.com/cold-soda-jay/iliaD/blob/master/pic/title.png?raw=true)

> **Important:** The project is now only support Ilias platform of ***Karlsruhe Institut für Technologie***.


# IliaD-Ilias7

Due to the upgrade to Ilias 7, the original functions in IliaD no longer work. Therefore, I have modified the label recognition part of IliaD and developed a new version, named IliaD-Ilias7, to scrape Ilias effectively.


## Install 

This is the legacy version. While it can be installed directly from pip, it does not work with Ilias 7:

```
$ pip install iliaDownloader

$ iliaD
```

To use this program with Ilias 7, you should clone this repository, then install it using pip in editable mode, and finally initialize the configuration using iliaD init:

```
$ git clone https://github.com/Virlight/IliaD-Ilias7.git
$ cd IliaD-Ilias7
$ pip install -e .
$ iliaD init
```

</br>

**&diams; Requirement if using source code**

```python
beautifulsoup4==4.9.0
bs4==0.0.1
requests==2.23.0
urllib3==1.25.9
soupsieve==2.0
texttable==1.6.2
```
## Usage

</br>

**&diams; Initiate**

``iliaD init`` 

or

``iliaD init -name uxxxx -target path/of/target``

For the first time to use you should use command ``init`` to initiate the user information. Follow the constructions you can set your user name in form "**uxxxx**", the **password** and the path of **target directory**.

``iliaD course``


After user data initiated, you can use command ``course`` to choose courses to be downloaded. Or you can use command ``sync`` to choose courses and download the directly.

</br>

**&diams; Synchronize**

``iliaD sync``

Use command ``sync`` you can synchronize new files. The exist file will not be changed. Only new file in ilias will be downloaded to the folder.

</br>

**&diams; Check user data and edit**

``iliaD user``

or

``iliaD course``

Use command ``user`` to check and edit the user name, target directory and password. Use command ``course`` to check and edit marked courses.


## Commands

|Command | Usage |
|:-:|:-:|
| ``init`` |Init user config with name and target folder |
|``sync`` |Synchronize all marked Ilias files |
|``user`` | Print or change user data|
|``course`` |Print or change marked courses |


## Automatic daily synchronization

If you have a raspberry pi or any Unix computer, you can do the following instructions to synchronize the ilias folder with your cloud storage.

1. Download the [iliaD](https://github.com/cold-soda-jay/iliaD) .
2. Download [rclone](https://rclone.org/) .
3. Bind rclone with your cloud storage.
4. Initiate the iliaD, set the target directory (e.g. ``/home/pi/Onedrive/SS20/``)
5. Open crontab: with ``crontab -e`` in terminal
6. Add following instructions:
    1. ``00 05 * * * iliaD sync >> /path/of/iliaD.log 2>&1``
    2. ``30 05 * * * rclone -v copy path/of/target/directory/ path_of_cloud >> path/of/rclone.log 2>&1``

With the seetings, your raspberry pi will synchronize the ilias folder, download new files at 5:00 am. and upload them in your cloud storage at 5:30 am.

## Automatic daily synchronization in IliaD-Ilias7

In IliaD-Ilias7, there is a script named ``run_iliaD.sh``. You can edit your crontab to set up automatic daily synchronization. However, this method is only applicable in Linux and MacOS environments.

1. Open crontab: with ``crontab -e`` in terminal
2. Add following instructions: ``00 05 * * * path/to/run_iliaD.sh``. This command schedules the synchronization of materials every day at 5 a.m.
