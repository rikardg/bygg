import dataclasses
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Optional, Union

import dacite
import dc_schema  # type: ignore

from bygg.output.output import TerminalStyle as TS
from bygg.output.output import output_plain

PYTHON_INPUTFILE = "Byggfile.py"
TOML_INPUTFILE = "Byggfile.toml"
YAML_INPUTFILE = "Byggfile.yml"

BYGGFILE_SUFFIXES = (".toml", ".yml", ".py")

DEFAULT_ENVIRONMENT_NAME = "_BYGG_DEFAULT_NULL_ENVIRONMENT"


@dataclasses.dataclass
class Settings:
    __doc__ = """
    The global settings object for Bygg.
    """

    def merge(self, other: "Settings"):
        """
        Merges the settings with another Settings object.
        """
        if other.default_action is not None:
            self.default_action = other.default_action
        if other.verbose is not None:
            self.verbose = other.verbose

    default_action: Optional[str] = None
    verbose: Optional[bool] = None


@dataclasses.dataclass
class ActionItem:
    """
    This is a representation of the Action class used for deserialising from YAML.
    The name of the action is the key in the dictionary in the config file.

    Parameters
    ----------
    description : str, optional
        A description of the action. Used in e.g. action listings. Default is None.
    message : str, optional
        A message to print when the action is executed. Default is None.
    inputs : list of str, optional
        A list of files that are used as input to the action. Default is None.
    outputs : list of str, optional
        A list of files that are generated by the action. Default is None.
    dependencies : list of str, optional
        A list of actions that must be executed before this action. Default is None.
    is_entrypoint : bool, optional
        Whether this action is an entrypoint. Entrypoints are actions that can be
        executed directly from the command line. If not set, this is treated as true by
        default in Byggfile.yml and false when used from Python. Default is None.
    environment : str, optional
        The environment for the action. Default is to run in the ambient environment.
    shell : str, optional
        The shell command to execute when the action is run. Default is None.
    """

    description: Optional[str] = None
    message: Optional[str] = None
    inputs: Optional[list[str]] = None
    outputs: Optional[list[str]] = None
    dependencies: Optional[list[str]] = None
    is_entrypoint: Optional[bool] = None
    environment: Optional[str] = DEFAULT_ENVIRONMENT_NAME
    shell: Optional[str] = None


@dataclasses.dataclass
class Environment:
    """
    A class used to represent a virtual environment that actions can be run in.

    Attributes
    ----------
    inputs : list[str]
        A list of files that are used as input to the environment. Typically pip
        requirements files, but can be any files.
    venv_directory : str
        The directory where the virtual environment is located. Will be recreated by
        Bygg if any of the inputs are modified.
    shell : str
        The shell command for creating the environment.
    byggfile : str
        The Python Byggfile that uses this environment. This is the entrypoint for where
        actions declared in Python are looked up. Optional.
    name : str, optional
        A human-friendly name for the environment. Used in e.g. help messages, by
        default None
    """

    inputs: list[str]
    venv_directory: str
    shell: str
    byggfile: Optional[str] = None
    name: Optional[str] = None


@dataclasses.dataclass
class Byggfile:
    class SchemaConfig:
        annotation = dc_schema.SchemaAnnotation(
            title="Schema for the configuration files for Bygg",
        )

    # Have to use Union here since dc_schema doesn't support the | notation
    actions: dict[str, Union[ActionItem, str]] = dataclasses.field(default_factory=dict)
    settings: Settings = dataclasses.field(default_factory=Settings)
    environments: dict[str, Environment] = dataclasses.field(default_factory=dict)


def has_byggfile() -> bool:
    """
    Checks if a Byggfile (in any format, including Python) exists in the current
    directory.

    Returns
    -------
    bool
        True if a Byggfile exists, False otherwise.
    """
    return len(get_config_files()) > 0 or os.path.isfile(PYTHON_INPUTFILE)


def get_config_files() -> list[Path]:
    """
    Checks if a static config file (a Byggfile that is not written in Python) is present
    in the current directory.
    """
    return [p for p in [Path(TOML_INPUTFILE), Path(YAML_INPUTFILE)] if p.is_file()]


def read_config_files() -> Byggfile:
    """Read all static config files and return them merged into one Byggfile object."""
    config_files = get_config_files()
    if not config_files:
        return Byggfile(actions={}, settings=Settings(), environments={})

    def action_item_hook(val):
        if isinstance(val, str):
            # Convert shortform actions to objects
            return ActionItem(shell=val)
        return dacite.from_dict(data=val, data_class=ActionItem)

    dacite_config = dacite.Config(
        strict=True,
        type_hooks={ActionItem: action_item_hook},
    )

    try:
        byggfile_objects: list[Byggfile] = []
        for cf in config_files:
            match cf.suffix:
                case ".toml":
                    import tomllib

                    with cf.open("rb") as toml_file:
                        byggfile_objects.append(
                            dacite.from_dict(
                                config=dacite_config,
                                data=tomllib.load(toml_file),
                                data_class=Byggfile,
                            )
                        )
                case ".yml":
                    import yaml

                    with cf.open("r", encoding="utf-8") as yaml_file:
                        byggfile_objects.append(
                            dacite.from_dict(
                                config=dacite_config,
                                data=yaml.safe_load(yaml_file),
                                data_class=Byggfile,
                            )
                        )
                case _:
                    raise ValueError(f"Unknown file extension {cf.suffix}")

        for bfo in byggfile_objects:
            for _, action in bfo.actions.items():
                if TYPE_CHECKING:
                    assert not isinstance(action, str)
                # Actions in byggfiles are entrypoints by default, unlike the actions
                # declared in Python files
                if action.is_entrypoint is None:
                    action.is_entrypoint = True
        return merge_byggfiles(byggfile_objects)

    except Exception as e:
        output_plain(
            TS.Fg.RED
            + " Error while reading configuration file."
            + TS.Fg.RESET
            + f" {e}"
        )
        sys.exit(1)


def merge_byggfiles(byggfiles: list[Byggfile]) -> Byggfile:
    """
    Merges a list of Byggfile objects into a single one.
    """
    merged_byggfile = Byggfile()
    for bf in byggfiles:
        merged_byggfile.actions.update(bf.actions)
        merged_byggfile.settings.merge(bf.settings)
        merged_byggfile.environments.update(bf.environments)
    return merged_byggfile


def dump_schema():
    import json
    import textwrap

    schema = dc_schema.get_schema(Byggfile)

    # Additional properties are not allowed, but dc_schema does not yet support this.
    # See https://github.com/Peter554/dc_schema/issues/6 .
    schema["additionalProperties"] = False

    classes_to_properties = {
        "ActionItem": "actions",
        "Environment": "environments",
        "Settings": "settings",
    }

    for k in schema["$defs"].keys():
        if k in classes_to_properties:
            schema["$defs"][k]["title"] = k
            schema["$defs"][k]["additionalProperties"] = False
            docstring = globals()[k].__doc__
            if docstring is not None:
                # Add the docstrings to the field types
                formatted_docstring = textwrap.dedent(docstring).strip()
                schema["$defs"][k]["description"] = formatted_docstring

                # Also add the docstrings to the containers
                schema["properties"][classes_to_properties[k]]["title"] = k
                schema["properties"][classes_to_properties[k]]["description"] = (
                    formatted_docstring
                )

    print(json.dumps(schema, indent=2))
