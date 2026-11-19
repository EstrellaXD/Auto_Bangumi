from pydantic import BaseModel

from ab_sdk import Plugin, points, provider
from ab_sdk.admission import Admission, AdmissionRequest


class Options(BaseModel):
    approved: bool = False


class Review(Plugin[Options]):
    config_model = Options

    @provider(points.DOWNLOAD_PREFLIGHT, id="review")
    def gate(self):
        return self

    async def preflight(self, request: AdmissionRequest) -> Admission:
        if not self.config.approved:
            return Admission("hold", "Choose a version first")
        for candidate in request.candidates:
            release = candidate.release
            if release is None or release.episode is None:
                return Admission("hold", "Episode needs review")
            batch = await self.ctx.downloads.candidates(batch_id=candidate.batch_id, limit=500)
            if batch.cursor is not None:
                return Admission("hold", "Read all candidate pages before approving")
            for other in batch.items:
                newer = other.release
                if (other.bangumi_id == request.bangumi.id and other.stage == "matched"
                    and newer is not None and newer.episode == release.episode
                    and newer.group == release.group and newer.subtitle == release.subtitle
                    and newer.resolution == release.resolution and newer.source == release.source
                    and (newer.version or 1) > (release.version or 1)):
                    return Admission("reject", "A newer revision is available in this batch")
        return Admission("allow")
