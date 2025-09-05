from typing import List
from services.orchestrator.db_clients import get_companies_by_icp

def discoverProspects(configId: str, topK: int = 200) -> List[str]:
    """
    Return up to topK companyIds that match the ICP for the given configId.
    Right now this delegates to db_clients.get_companies_by_icp(configId).
    Later you can add filters (industry, geo, size, tech) inside that helper.
    """
    companyIds = get_companies_by_icp(configId)
    # SAFETY: de-dup and trim to topK
    seen = set()
    deduped = []
    for cid in companyIds:
        if cid and cid not in seen:
            seen.add(cid)
            deduped.append(cid)
        if len(deduped) >= topK:
            break
    return deduped
