from app.connectors.adverse_news import AdverseNewsConnector
from app.connectors.base import ScreeningConnector
from app.connectors.ctos import CTOSConnector
from app.connectors.netreveal import NetRevealConnector
from app.connectors.prior_kyv import PriorKYVConnector
from app.connectors.public_records import PublicRecordsConnector
from app.schemas.screening import SourceName

CONNECTOR_REGISTRY: dict[SourceName, ScreeningConnector] = {
    SourceName.CTOS: CTOSConnector(),
    SourceName.NETREVEAL: NetRevealConnector(),
    SourceName.PRIOR_KYV: PriorKYVConnector(),
    SourceName.ADVERSE_NEWS: AdverseNewsConnector(),
    SourceName.PUBLIC_RECORDS: PublicRecordsConnector(),
}
