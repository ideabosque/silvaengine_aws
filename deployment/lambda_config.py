lambdaConfig = {
    "functions": {
        "silvaengine_area_resource": {
            "update": True,
            "base": "/api",
            "packages": [],
            "package_files": [],
            "files": {}
        },
        "silvaengine_microcore": {
            "update": True,
            "base": "/beehive/microcore",
            "packages": [],
            "package_files": [],
            "files": {}
        }
    },
    "layers": {
        "silvaengine_layer": {
            "update": True,
            "packages": [
                "silvaengine_utility",
                "sample_module",
                "datawald_interface",
                "datawald_model",
                "pynamodb",
                "dateutil",
                "graphene",
                "aniso8601",
                "graphql",
                "graphql_relay",
                "rx",
                "promise"
            ],
            "package_files": [
            ],
            "files": {}
        }
    }
}