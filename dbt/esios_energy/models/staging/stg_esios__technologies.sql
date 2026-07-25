select
    indicator_id,
    technology_name,
    technology_group,
    is_renewable
from {{ ref('technologies') }} -- Recogido de la tabla csv de referencia, no de ESIOS