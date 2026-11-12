{# A reusable test. A dbt test is a query that returns the rows that are WRONG.
   Zero rows back means the test passes. #}
{% test value_between(model, column_name, min_value, max_value) %}

select *
from {{ model }}
where {{ column_name }} < {{ min_value }}
   or {{ column_name }} > {{ max_value }}

{% endtest %}
