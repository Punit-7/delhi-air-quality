{# By default dbt would name the schemas "staging_staging" and "staging_marts".
   This override makes "+schema: marts" mean exactly "marts". #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
