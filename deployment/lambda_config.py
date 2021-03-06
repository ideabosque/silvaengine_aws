lambdaConfig = {
    "functions": {
        "silvaengine_area_resource": {
            "update": False,
            "base": "/api",
            "packages": [],
            "package_files": [],
            "files": {}
        },
        "silvaengine_agenttask": {
            "update": True,
            "base": "/taskqueue/agenttask",
            "packages": [],
            "package_files": [],
            "files": {}
        },
        "silvaengine_microcore": {
            "update": False,
            "base": "/beehive/microcore",
            "packages": [],
            "package_files": [],
            "files": {}
        }
    },
    "layers": {
        "silvaengine_layer": {
            "update": False,
            "packages": [
                "silvaengine_utility",
                "pynamodb",
                "dateutil",
                "graphene",
                "aniso8601",
                "graphql",
                "graphql_relay",
                "rx",
                "promise",
                "requests",
                "urllib3",
                "chardet",
                "certifi",
                "idna"
            ],
            "package_files": [
            ],
            "files": {}
        },
        "silvaengine_microcore_layer": {
            "update": False,
            "packages": [
                "sample_module",
                "datawald_interface",
                "datawald_model"
            ],
            "package_files": [
            ],
            "files": {}
        }
    }
}