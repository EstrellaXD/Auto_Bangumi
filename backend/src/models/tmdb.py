from pydantic import BaseModel, Field


class ShowInfo(BaseModel):
    """TMDB 搜索结果中的单个节目信息"""

    adult: bool = Field(default=False, title="是否成人内容")
    backdrop_path: str | None = Field(default=None, title="背景图路径")
    genre_ids: list[int] = Field(default_factory=list, title="类型ID列表")
    id: int = Field(..., title="TMDB ID")
    origin_country: list[str] = Field(default_factory=list, title="原产国")
    original_language: str = Field(default="", title="原始语言")
    original_name: str = Field(default="", title="原始名称")
    overview: str = Field(default="", title="简介")
    popularity: float = Field(default=0.0, title="热度")
    poster_path: str | None = Field(default=None, title="海报路径")
    first_air_date: str | None = Field(default=None, title="首播日期")
    name: str = Field(default="", title="名称")
    vote_average: float = Field(default=0.0, title="评分")
    vote_count: int = Field(default=0, title="评分人数")


class Genre(BaseModel):
    """节目类型"""

    id: int = Field(..., title="类型ID")
    name: str = Field(default="", title="类型名称")


class Network(BaseModel):
    """电视网络/平台"""

    id: int = Field(..., title="网络ID")
    logo_path: str | None = Field(default=None, title="Logo路径")
    name: str = Field(default="", title="网络名称")
    origin_country: str = Field(default="", title="所属国家")


class LastEpisodeToAir(BaseModel):
    """最后播出的剧集信息"""

    id: int = Field(..., title="剧集ID")
    name: str = Field(default="", title="剧集名称")
    overview: str = Field(default="", title="剧集简介")
    vote_average: float = Field(default=0.0, title="评分")
    vote_count: int = Field(default=0, title="评分人数")
    air_date: str | None = Field(default=None, title="播出日期")
    episode_number: int = Field(default=0, title="集数")
    episode_type: str = Field(default="", title="剧集类型")
    production_code: str = Field(default="", title="制作代码")
    runtime: int | None = Field(default=None, title="时长(分钟)")
    season_number: int = Field(default=0, title="季数")
    show_id: int = Field(default=0, title="节目ID")
    still_path: str | None = Field(default=None, title="剧照路径")


class ProductionCompany(BaseModel):
    """制作公司"""

    id: int = Field(..., title="公司ID")
    name: str = Field(default="", title="公司名称")
    origin_country: str = Field(default="", title="所属国家")
    logo_path: str | None = Field(default=None, title="Logo路径")


class SeasonTMDB(BaseModel):
    """TMDB 季度信息"""

    air_date: str | None = Field(default=None, title="播出日期")
    episode_count: int = Field(default=0, title="集数")
    id: int = Field(..., title="季度ID")
    name: str = Field(default="", title="季度名称")
    overview: str = Field(default="", title="季度简介")
    poster_path: str | None = Field(default=None, title="海报路径")
    season_number: int = Field(default=0, title="季数")
    vote_average: float = Field(default=0.0, title="评分")


class TVShow(BaseModel):
    """TMDB 节目详细信息"""

    adult: bool = Field(default=False, title="是否成人内容")
    backdrop_path: str | None = Field(default=None, title="背景图路径")
    created_by: list = Field(default_factory=list, title="创作者")
    episode_run_time: list[int] = Field(default_factory=list, title="单集时长列表")
    first_air_date: str | None = Field(default=None, title="首播日期")
    genres: list[Genre] = Field(default_factory=list, title="类型列表")
    homepage: str = Field(default="", title="官网地址")
    id: int = Field(..., title="TMDB ID")
    in_production: bool = Field(default=False, title="是否在制作中")
    languages: list[str] = Field(default_factory=list, title="语言列表")
    last_air_date: str | None = Field(default=None, title="最后播出日期")
    last_episode_to_air: LastEpisodeToAir | None = Field(default=None, title="最后播出剧集")
    name: str = Field(default="", title="名称")
    networks: list[Network] = Field(default_factory=list, title="播出平台列表")
    number_of_episodes: int = Field(default=0, title="总集数")
    number_of_seasons: int = Field(default=0, title="总季数")
    origin_country: list[str] = Field(default_factory=list, title="原产国")
    original_language: str = Field(default="", title="原始语言")
    original_name: str = Field(default="", title="原始名称")
    overview: str = Field(default="", title="简介")
    popularity: float = Field(default=0.0, title="热度")
    poster_path: str | None = Field(default=None, title="海报路径")
    production_companies: list[ProductionCompany] = Field(default_factory=list, title="制作公司列表")
    production_countries: list[dict[str, str]] = Field(default_factory=list, title="制作国家列表")
    seasons: list[SeasonTMDB] = Field(default_factory=list, title="季度列表")
    next_episode_to_air: LastEpisodeToAir | None = Field(default=None, title="下一集播出信息")
    vote_average: float = Field(default=0.0, title="评分")
    vote_count: int = Field(default=0, title="评分人数")


class SearchResult(BaseModel):
    """TMDB 搜索结果"""

    page: int = Field(default=1, title="当前页码")
    results: list[ShowInfo] = Field(default_factory=list, title="搜索结果列表")
    total_pages: int = Field(default=0, title="总页数")
    total_results: int = Field(default=0, title="总结果数")


class TMDBInfo(BaseModel):
    """解析后的 TMDB 信息"""

    id: int = Field(...,  title="TMDB ID")
    year: str = Field(default="", title="番剧年份")
    original_title: str = Field(default="", title="番剧原名")
    air_date: str = Field(default="", title="首播日期")
    episode_count: int = Field(default=0, title="总集数")
    title: str = Field(default="", title="番剧名称")
    season: int = Field(default=1, title="季度")
    poster_link: str = Field(default="", title="海报链接")
    vote_average: float = Field(default=0.0, title="评分")
