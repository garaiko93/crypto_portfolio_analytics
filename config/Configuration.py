import configparser

class Configuration():
    def getConfig(self, configPath, section="DEFAULT"):
        config = configparser.ConfigParser()
        config.read(configPath)

        return config[section]
