# Dependency management with pip

## Requirements
* pip
* requirements.txt
* Package [tqdm](https://github.com/tqdm/tqdm) gives you great visualization of ongoing process, but it's not required.

## Background / Description
With pip command and requirements.txt file, you can manage Python modules required to manage a project. However, it is hard to keep track of dependencies. This standalone script will allow you to create `requirements.json` file, with which you can track dependencies of packages required for your project.

For example, if you install [tensorflow](https://github.com/tensorflow/tensorflow) package (v1.3) through pip, following packages will be installed at the same time; `bleach`, `html5lib`, `markdown`, `numpy`, `protobuf`, `tensorflow-tensorboard`, `werkzeug`. If you no longer need tensorflow package, it is highly likely you want to remove all the packages related to it. The problem is that dependencies listed above might be another package's dependency. So you need to run `pip show` recursively to check dependencies that will not affect other required modules. This script will take care of it.

## Usage
First of all, you will have to create `requirements.json` file with the following command;
```
$ python dependencies.py --config
```
When you want to uninstall packages, run the following command to see what other packages can be uninstalled at the same time;
```
$ python dependencies.py --delete package-name
```
As your project grows, you might forget what packages you or collaborators installed. You can list, with the following command, packages that are not any packages' dependency;
```
$ python dependencies.py --check
```

## Create Alias
Since this is a standalone script, it is recommended to create alias;
```
$ alias pip_manage="python path/to/dependencies.py"
```
By not specifying absolute path to Python, you can call the command from different virtualenv environments if that is something you use.

Once you create alias, all you have to do is to call the alias you created with arguments like the following;
```
$ pip_manage --config
```

## License
Apache License 2.0