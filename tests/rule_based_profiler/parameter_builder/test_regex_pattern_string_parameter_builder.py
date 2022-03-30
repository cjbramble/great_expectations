from typing import List, Set
from unittest import mock
from unittest.mock import MagicMock

import pandas as pd
import pytest

import great_expectations.exceptions as ge_exceptions
from great_expectations.core.batch import (
    Batch,
    BatchDefinition,
    BatchMarkers,
    BatchRequest,
)
from great_expectations.core.id_dict import BatchSpec, IDDict
from great_expectations.data_context import DataContext
from great_expectations.execution_engine import PandasExecutionEngine
from great_expectations.execution_engine.execution_engine import MetricDomainTypes
from great_expectations.rule_based_profiler.helpers.util import (
    get_parameter_value_and_validate_return_type,
)
from great_expectations.rule_based_profiler.parameter_builder import (
    RegexPatternStringParameterBuilder,
)
from great_expectations.rule_based_profiler.types import (
    Domain,
    ParameterContainer,
    get_parameter_value_by_fully_qualified_parameter_name,
)
from great_expectations.validator.validator import Validator


@pytest.fixture
def batch_fixture() -> Batch:
    """
    Fixture for Batch object that contains data, BatchRequest, BatchDefinition
    as well as BatchSpec and BatchMarkers. To be used in unittesting.
    """
    df: pd.DataFrame = pd.DataFrame(
        {"a": [1, 5, 22, 3, 5, 10], "b": [1, 2, 3, 4, 5, 6]}
    )
    batch_request: BatchRequest = BatchRequest(
        datasource_name="my_datasource",
        data_connector_name="my_data_connector",
        data_asset_name="my_data_asset_name",
    )
    batch_definition: BatchDefinition = BatchDefinition(
        datasource_name="my_datasource",
        data_connector_name="my_data_connector",
        data_asset_name="my_data_asset_name",
        batch_identifiers=IDDict({"id": "A"}),
    )
    batch_spec: BatchSpec = BatchSpec(path="/some/path/some.file")
    batch_markers: BatchMarkers = BatchMarkers(ge_load_time="FAKE_LOAD_TIME")
    batch: Batch = Batch(
        data=df,
        batch_request=batch_request,
        batch_definition=batch_definition,
        batch_spec=batch_spec,
        batch_markers=batch_markers,
    )
    return batch


@mock.patch("great_expectations.data_context.data_context.DataContext")
def test_regex_pattern_string_parameter_builder_instantiation_with_defaults(
    mock_data_context: mock.MagicMock,
):
    data_context: DataContext = mock_data_context

    candidate_regexes: Set[str] = {
        r"/\d+/",  # whole number with 1 or more digits
        r"/-?\d+/",  # negative whole numbers
        r"/-?\d+(\.\d*)?/",  # decimal numbers with . (period) separator
        r"/[A-Za-z0-9\.,;:!?()\"'%\-]+/",  # general text
        r"^\s+/",  # leading space
        r"\s+/$",  # trailing space
        r"/https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#()?&//=]*)/",  # Matching URL (including http(s) protocol)
        r"/<\/?(?:p|a|b|img)(?: \/)?>/",  # HTML tags
        r"/(?:25[0-5]|2[0-4]\d|[01]\d{2}|\d{1,2})(?:.(?:25[0-5]|2[0-4]\d|[01]\d{2}|\d{1,2})){3}/",  # IPv4 IP address
        r"/(?:[A-Fa-f0-9]){0,4}(?: ?:? ?(?:[A-Fa-f0-9]){0,4}){0,7}/",  # IPv6 IP address,
        r"\b[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}-[0-5][0-9a-fA-F]{3}-[089ab][0-9a-fA-F]{3}-\b[0-9a-fA-F]{12}\b ",  # UUID
    }

    regex_pattern_string_parameter: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            data_context=data_context,
            candidate_regexes=candidate_regexes,
        )
    )

    assert regex_pattern_string_parameter.threshold == 1.0
    assert regex_pattern_string_parameter.candidate_regexes == candidate_regexes
    assert regex_pattern_string_parameter.CANDIDATE_REGEX == candidate_regexes


@mock.patch("great_expectations.data_context.data_context.DataContext")
def test_regex_pattern_string_parameter_builder_instantiation_override_defaults(
    mock_data_context: mock.MagicMock,
):
    data_context: DataContext = mock_data_context

    candidate_regexes: Set[str] = {
        r"\d{1}",
    }
    regex_pattern_string_parameter: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            candidate_regexes=candidate_regexes,
            threshold=0.5,
            data_context=data_context,
        )
    )
    assert regex_pattern_string_parameter.threshold == 0.5
    assert regex_pattern_string_parameter.candidate_regexes == candidate_regexes
    assert regex_pattern_string_parameter.CANDIDATE_REGEX != candidate_regexes


def test_regex_pattern_string_parameter_builder_alice(
    alice_columnar_table_single_batch_context,
):
    data_context: DataContext = alice_columnar_table_single_batch_context

    batch_request: dict = {
        "datasource_name": "alice_columnar_table_single_batch_datasource",
        "data_connector_name": "alice_columnar_table_single_batch_data_connector",
        "data_asset_name": "alice_columnar_table_single_batch_data_asset",
    }

    metric_domain_kwargs = {"column": "id"}
    candidate_regexes: List[str] = [
        r"^\d{1}$",
        r"^\d{2}$",
        r"^\S{8}-\S{4}-\S{4}-\S{4}-\S{12}$",
    ]

    regex_pattern_string_parameter: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            batch_request=batch_request,
            data_context=data_context,
        )
    )

    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )
    assert parameter_container.parameter_nodes is None

    regex_pattern_string_parameter.build_parameters(
        parameter_container=parameter_container, domain=domain
    )
    fully_qualified_parameter_name_for_value: str = (
        "$parameter.my_regex_pattern_string_parameter_builder"
    )
    expected_value: dict = {
        "value": r"^\S{8}-\S{4}-\S{4}-\S{4}-\S{12}$",
        "details": {
            "evaluated_regexes": {
                r"^\S{8}-\S{4}-\S{4}-\S{4}-\S{12}$": 1.0,
                r"^\d{1}$": 0,
                r"^\d{2}$": 0,
            },
            "threshold": 1.0,
        },
    }

    assert (
        get_parameter_value_by_fully_qualified_parameter_name(
            fully_qualified_parameter_name=fully_qualified_parameter_name_for_value,
            domain=domain,
            parameters={domain.id: parameter_container},
        )
        == expected_value
    )


def test_regex_pattern_string_parameter_builder_bobby_multiple_matches(
    bobby_columnar_table_multi_batch_deterministic_data_context,
):
    data_context: DataContext = (
        bobby_columnar_table_multi_batch_deterministic_data_context
    )

    batch_request: dict = {
        "datasource_name": "taxi_pandas",
        "data_connector_name": "monthly",
        "data_asset_name": "my_reports",
        "data_connector_query": {"index": -1},
    }

    metric_domain_kwargs: dict = {"column": "VendorID"}

    candidate_regexes: List[str] = [
        r"^\d{1}$",  # will match
        r"^[12]{1}$",  # will match 0.9941111111 of the time
        r"^\d{4}$",  # won't match
    ]
    threshold: float = 0.9

    regex_parameter: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            threshold=threshold,
            batch_request=batch_request,
            data_context=data_context,
        )
    )

    assert regex_parameter.CANDIDATE_REGEX != candidate_regexes
    assert regex_parameter.candidate_regexes == candidate_regexes
    assert regex_parameter.threshold == 0.9

    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )

    assert parameter_container.parameter_nodes is None

    regex_parameter.build_parameters(
        parameter_container=parameter_container, domain=domain
    )

    fully_qualified_parameter_name_for_value: str = (
        "$parameter.my_regex_pattern_string_parameter_builder"
    )
    expected_value: dict = {
        "value": r"^\d{1}$",
        "details": {
            "evaluated_regexes": {
                r"^\d{1}$": 1.0,
                r"^[12]{1}$": 0.9941111111111111,
                r"^\d{4}$": 0,
            },
            "threshold": 0.9,
        },
    }

    results = get_parameter_value_by_fully_qualified_parameter_name(
        fully_qualified_parameter_name=fully_qualified_parameter_name_for_value,
        domain=domain,
        parameters={domain.id: parameter_container},
    )
    assert results is not None
    assert sorted(results["value"]) == sorted(expected_value["value"])
    assert results["details"] == expected_value["details"]


def test_regex_pattern_string_parameter_builder_bobby_no_match(
    bobby_columnar_table_multi_batch_deterministic_data_context,
):
    data_context: DataContext = (
        bobby_columnar_table_multi_batch_deterministic_data_context
    )

    batch_request: dict = {
        "datasource_name": "taxi_pandas",
        "data_connector_name": "monthly",
        "data_asset_name": "my_reports",
        "data_connector_query": {"index": -1},
    }

    metric_domain_kwargs: dict = {"column": "VendorID"}

    candidate_regexes: Set[str] = {
        r"^\d{3}$",  # won't match
    }
    threshold: float = 0.9

    regex_parameter: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            threshold=threshold,
            batch_request=batch_request,
            data_context=data_context,
        )
    )
    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )

    assert parameter_container.parameter_nodes is None

    regex_parameter.build_parameters(
        parameter_container=parameter_container, domain=domain
    )

    fully_qualified_parameter_name_for_value: str = (
        "$parameter.my_regex_pattern_string_parameter_builder"
    )
    expected_value: dict = {
        "value": None,
        "details": {
            "evaluated_regexes": {
                r"/\d+/": 0,
                r"/-?\d+/": 0,
                r"/-?\d+(\.\d*)?/": 0,
                r"/[A-Za-z0-9\.,;:!?()\"'%\-]+/": 0,
                r"^\s+/": 0,
                r"\s+/$": 0,
                r"/https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#()?&//=]*)/": 0,
                r"/<\/?(?:p|a|b|img)(?: \/)?>/": 0,
                r"/(?:25[0-5]|2[0-4]\d|[01]\d{2}|\d{1,2})(?:.(?:25[0-5]|2[0-4]\d|[01]\d{2}|\d{1,2})){3}/": 0,
                r"/(?:[A-Fa-f0-9]){0,4}(?: ?:? ?(?:[A-Fa-f0-9]){0,4}){0,7}/": 0,
                r"\b[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}-[0-5][0-9a-fA-F]{3}-[089ab][0-9a-fA-F]{3}-\b[0-9a-fA-F]{12}\b ": 0,
            },
            "threshold": 0.9,
        },
    }

    assert (
        get_parameter_value_by_fully_qualified_parameter_name(
            fully_qualified_parameter_name=fully_qualified_parameter_name_for_value,
            domain=domain,
            parameters={domain.id: parameter_container},
        )
        == expected_value
    )


@mock.patch("great_expectations.data_context.data_context.DataContext")
def test_regex_wrong_domain(mock_data_context: mock.MagicMock, batch_fixture: Batch):
    batch: Batch = batch_fixture
    mock_data_context.get_batch_list.return_value = [batch]
    mock_data_context.get_validator_using_batch_list.return_value = Validator(
        execution_engine=PandasExecutionEngine(), batches=[batch]
    )

    data_context: DataContext = mock_data_context

    # column : c does not exist
    metric_domain_kwargs: dict = {"column": "c"}
    candidate_regexes: List[str] = [r"^\d{1}$"]

    regex_pattern_string_parameter_builder: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            batch_list=[batch],
            data_context=data_context,
        )
    )

    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )
    with pytest.raises(ge_exceptions.ProfilerExecutionError) as e:
        regex_pattern_string_parameter_builder.build_parameters(
            parameter_container=parameter_container, domain=domain
        )

    assert (
        e.value.message
        == "column_values.nonnull.count was not found in the resolved Metrics for ParameterBuilder."
    )


@mock.patch("great_expectations.data_context.data_context.DataContext")
def test_regex_single_candidate(
    mock_data_context: mock.MagicMock, batch_fixture: Batch
):
    batch: Batch = batch_fixture
    mock_data_context.get_batch_list.return_value = [batch]
    mock_data_context.get_validator_using_batch_list.return_value = Validator(
        execution_engine=PandasExecutionEngine(), batches=[batch]
    )

    data_context: DataContext = mock_data_context

    metric_domain_kwargs: dict = {"column": "b"}
    candidate_regexes: List[str] = [r"^\d{1}$"]

    regex_pattern_string_parameter_builder: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            batch_list=[batch],
            data_context=data_context,
        )
    )

    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )
    assert parameter_container.parameter_nodes is None

    regex_pattern_string_parameter_builder.build_parameters(
        parameter_container=parameter_container, domain=domain
    )
    fully_qualified_parameter_name_for_value: str = (
        "$parameter.my_regex_pattern_string_parameter_builder.value"
    )
    expected_value: str = "^\\d{1}$"
    assert (
        get_parameter_value_and_validate_return_type(
            parameter_reference=fully_qualified_parameter_name_for_value,
            expected_return_type=str,
            domain=domain,
            parameters={domain.id: parameter_container},
        )
        == expected_value
    )

    fully_qualified_parameter_name_for_meta: str = (
        "$parameter.my_regex_pattern_string_parameter_builder.details"
    )
    expected_meta: dict = {"evaluated_regexes": {"^\\d{1}$": 1.0}, "threshold": 1.0}

    meta: dict = get_parameter_value_and_validate_return_type(
        parameter_reference=fully_qualified_parameter_name_for_meta,
        expected_return_type=dict,
        domain=domain,
        parameters={domain.id: parameter_container},
    )
    assert meta == expected_meta


@mock.patch("great_expectations.data_context.data_context.DataContext")
def test_regex_two_candidates(mock_data_context: mock.MagicMock, batch_fixture: Batch):
    batch: Batch = batch_fixture

    mock_data_context.get_batch_list.return_value = [batch]
    mock_data_context.get_validator_using_batch_list.return_value = Validator(
        execution_engine=PandasExecutionEngine(), batches=[batch]
    )
    data_context: DataContext = mock_data_context

    metric_domain_kwargs: dict = {"column": "b"}
    candidate_regexes: List[str] = [r"^\d{1}$", r"^\d{3}$"]

    regex_pattern_string_parameter_builder: RegexPatternStringParameterBuilder = (
        RegexPatternStringParameterBuilder(
            name="my_regex_pattern_string_parameter_builder",
            metric_domain_kwargs=metric_domain_kwargs,
            candidate_regexes=candidate_regexes,
            batch_list=[batch],
            data_context=data_context,
        )
    )

    parameter_container: ParameterContainer = ParameterContainer(parameter_nodes=None)
    domain: Domain = Domain(
        domain_type=MetricDomainTypes.COLUMN, domain_kwargs=metric_domain_kwargs
    )
    assert parameter_container.parameter_nodes is None

    regex_pattern_string_parameter_builder.build_parameters(
        parameter_container=parameter_container, domain=domain
    )
    fully_qualified_parameter_name_for_value: str = (
        "$parameter.my_regex_pattern_string_parameter_builder.value"
    )

    expected_value: str = "^\\d{1}$"

    assert (
        get_parameter_value_and_validate_return_type(
            parameter_reference=fully_qualified_parameter_name_for_value,
            domain=domain,
            parameters={domain.id: parameter_container},
        )
        == expected_value
    )
    fully_qualified_parameter_name_for_meta: str = (
        "$parameter.my_regex_pattern_string_parameter_builder.details"
    )
    expected_meta: dict = {
        "evaluated_regexes": {"^\\d{1}$": 1.0, "^\\d{3}$": 0.0},
        "threshold": 1.0,
    }
    meta: dict = get_parameter_value_and_validate_return_type(
        parameter_reference=fully_qualified_parameter_name_for_meta,
        expected_return_type=dict,
        domain=domain,
        parameters={domain.id: parameter_container},
    )

    assert meta == expected_meta
