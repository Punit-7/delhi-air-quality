{# India's National Air Quality Index, PM2.5 part only.
   Input: a 24-hour average PM2.5 concentration in µg/m³.
   Output: the CPCB sub-index from 0 to 500, a straight line inside each band. #}
{% macro pm25_sub_index(column) -%}
    least(500, round(
        case
            when {{ column }} is null then null
            when {{ column }} <= 30  then {{ column }} * 50.0 / 30
            when {{ column }} <= 60  then 50  + ({{ column }} - 30)  * 50.0 / 30
            when {{ column }} <= 90  then 100 + ({{ column }} - 60)  * 100.0 / 30
            when {{ column }} <= 120 then 200 + ({{ column }} - 90)  * 100.0 / 30
            when {{ column }} <= 250 then 300 + ({{ column }} - 120) * 100.0 / 130
            else 400 + ({{ column }} - 250) * 100.0 / 130
        end
    ))::int
{%- endmacro %}

{% macro aqi_category(index_column) -%}
    case
        when {{ index_column }} is null then null
        when {{ index_column }} <= 50  then 'Good'
        when {{ index_column }} <= 100 then 'Satisfactory'
        when {{ index_column }} <= 200 then 'Moderate'
        when {{ index_column }} <= 300 then 'Poor'
        when {{ index_column }} <= 400 then 'Very Poor'
        else 'Severe'
    end
{%- endmacro %}
