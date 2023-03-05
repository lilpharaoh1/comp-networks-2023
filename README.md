# Emran x Nadeep Computer Networks Project Two

## Set Up

## Prerequisites

### Required

* [Python](https://realpython.com/installing-python/)

### Recommended

* [Visual Studio Code](https://www.toolsqa.com/blogs/install-visual-studio-code/)
* [git](https://www.atlassian.com/git/tutorials/install-git)

We also recommend using Windows 11.

To clone this package into a workspace:

```
git clone https://github.com/lilpharaoh1/comp-networks-2023.git
```

Enter into the directory and install the required packages

```
pip install -r requirements.txt
```

Before running the repo, you will need to set the agent's ip in server_dests.json to your machines ip address. Your ip can be found by using the command below on Windows.

```
ipconfig
```

## Usage

Open a VS Code terminal and use the command 
```
python main.py
```

Open an additional terminal and run the same command but with the port numbers specified in server_dests.json as an argument. An example of this can be found below.

```
python main.py -p 9898
```

A generalised version of this command can be found below. You can specify the ip and port number for each agent you initialise via the command line. 

```
python main.py -s [IP] -p [PORT NUMBER]
```

You will be informed that nodes are communicating via the messages in the terminal. Also, each time a node receives an image from a unique ip and port number, it will save it in a folder named data. The presence of this folder should indicate the system is running. 

