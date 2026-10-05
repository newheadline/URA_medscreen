# AUTO-GENERATED: python -m scripts.gen_labs_model. Не править вручную —
# менять показатели нужно в common/labs.py и перегенерировать файл.
from pydantic import BaseModel, ConfigDict, Field


class Labs(BaseModel):
    """Числовая матрица показателей (одна строка = один пациент)."""
    model_config = ConfigDict(extra="forbid")

    hemoglobin: float = Field(ge=20, le=250, allow_inf_nan=False, description='Гемоглобин, г/л')
    RBC: float | None = Field(None, ge=0.5, le=9, allow_inf_nan=False, description='Эритроциты, 10^12/л')
    hematocrit: float | None = Field(None, ge=5, le=75, allow_inf_nan=False, description='Гематокрит, %')
    MCV: float | None = Field(None, ge=40, le=160, allow_inf_nan=False, description='Средний объём эритроцита, фл')
    MCH: float | None = Field(None, ge=10, le=60, allow_inf_nan=False, description='Среднее содержание Hb в эритроците, пг')
    MCHC: float | None = Field(None, ge=200, le=450, allow_inf_nan=False, description='Средняя концентрация Hb в эритроците, г/л')
    RDW: float | None = Field(None, ge=8, le=40, allow_inf_nan=False, description='Анизоцитоз эритроцитов, %')
    platelets: float | None = Field(None, ge=1, le=2000, allow_inf_nan=False, description='Тромбоциты, 10^9/л')
    WBC: float | None = Field(None, ge=0.1, le=500, allow_inf_nan=False, description='Лейкоциты, 10^9/л')
    reticulocytes: float | None = Field(None, ge=0, le=30, allow_inf_nan=False, description='Ретикулоциты, %')
    ferritin: float | None = Field(None, ge=0, le=10000, allow_inf_nan=False, description='Ферритин, мкг/л')
    serum_iron: float | None = Field(None, ge=0, le=100, allow_inf_nan=False, description='Железо сыворотки, мкмоль/л')
    transferrin: float | None = Field(None, ge=0, le=8, allow_inf_nan=False, description='Трансферрин, г/л')
    TIBC: float | None = Field(None, ge=10, le=150, allow_inf_nan=False, description='ОЖСС, мкмоль/л')
    UIBC: float | None = Field(None, ge=0, le=120, allow_inf_nan=False, description='НЖСС, мкмоль/л')
    TSAT: float | None = Field(None, ge=0, le=100, allow_inf_nan=False, description='Насыщение трансферрина, %')
    sTfR: float | None = Field(None, ge=0, le=30, allow_inf_nan=False, description='Растворимый рецептор трансферрина, мг/л')
    Ret_He: float | None = Field(None, ge=10, le=50, allow_inf_nan=False, description='Содержание Hb в ретикулоцитах, пг')
    vitamin_B12: float | None = Field(None, ge=0, le=5000, allow_inf_nan=False, description='Витамин B12, пг/мл')
    active_B12: float | None = Field(None, ge=0, le=500, allow_inf_nan=False, description='Активный B12 (холо-ТК), пмоль/л')
    MMA: float | None = Field(None, ge=0, le=20, allow_inf_nan=False, description='Метилмалоновая кислота, мкмоль/л')
    homocysteine: float | None = Field(None, ge=0, le=200, allow_inf_nan=False, description='Гомоцистеин, мкмоль/л')
    folate: float | None = Field(None, ge=0, le=100, allow_inf_nan=False, description='Фолаты, нг/мл')
    vitamin_B6: float | None = Field(None, ge=0, le=500, allow_inf_nan=False, description='Витамин B6, нмоль/л')
    copper: float | None = Field(None, ge=0, le=60, allow_inf_nan=False, description='Медь, мкмоль/л')
    ceruloplasmin: float | None = Field(None, ge=0, le=2, allow_inf_nan=False, description='Церулоплазмин, г/л')
    CRP: float | None = Field(None, ge=0, le=500, allow_inf_nan=False, description='С-реактивный белок, мг/л')
    ESR: float | None = Field(None, ge=0, le=150, allow_inf_nan=False, description='СОЭ, мм/ч')
    creatinine: float | None = Field(None, ge=10, le=2000, allow_inf_nan=False, description='Креатинин, мкмоль/л')
    eGFR: float | None = Field(None, ge=0, le=200, allow_inf_nan=False, description='рСКФ, мл/мин/1.73м²')
    TSH: float | None = Field(None, ge=0, le=200, allow_inf_nan=False, description='ТТГ, мМЕ/л')
    albumin: float | None = Field(None, ge=5, le=70, allow_inf_nan=False, description='Альбумин, г/л')
    LDH: float | None = Field(None, ge=0, le=10000, allow_inf_nan=False, description='ЛДГ, Ед/л')
    indirect_bilirubin: float | None = Field(None, ge=0, le=500, allow_inf_nan=False, description='Непрямой билирубин, мкмоль/л')
    haptoglobin: float | None = Field(None, ge=0, le=10, allow_inf_nan=False, description='Гаптоглобин, г/л')
