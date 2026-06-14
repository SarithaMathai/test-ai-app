"""GET /api/v1/departments — fetch distinct departments from TCIN records."""

from __future__ import annotations

from fastapi import APIRouter

from plm_tcin_mapper_api.dependencies import MongoDep

router = APIRouter(tags=["departments"])


@router.get("/departments")
async def get_departments(mongo: MongoDep = None) -> dict:
    """
    Get all distinct department IDs from TCIN records.

    Returns:
      {
        "departments": [list of distinct department IDs]
      }
    """
    db = mongo.get_db()
    departments = await db.tcin_records.distinct("department_ids")
    # Flatten nested arrays if necessary
    flat_depts = set()
    for dept_list in departments:
        if isinstance(dept_list, list):
            flat_depts.update(dept_list)
        else:
            flat_depts.add(dept_list)
    return {"departments": sorted(flat_depts)}
