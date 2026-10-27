from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession

etat = {}


@asynccontextmanager
async def lifespan(app):
    etat["spark"] = SparkSession.builder.master("local[1]").appName("api-champignons").getOrCreate()
    etat["model"] = PipelineModel.load("models/champignons_rf")
    yield
    etat["spark"].stop()


app = FastAPI(lifespan=lifespan)


class Champignon(BaseModel):
    cap_shape: str
    cap_surface: str
    cap_color: str
    bruises: str
    odor: str
    gill_attachment: str
    gill_spacing: str
    gill_size: str
    gill_color: str
    stalk_shape: str
    stalk_root: str
    stalk_surface_above_ring: str
    stalk_surface_below_ring: str
    stalk_color_above_ring: str
    stalk_color_below_ring: str
    veil_color: str
    ring_number: str
    ring_type: str
    spore_print_color: str
    population: str
    habitat: str


@app.post("/predict")
def predict(champignon: Champignon):
    ligne = etat["spark"].createDataFrame([champignon.model_dump()])
    res = etat["model"].transform(ligne).select("prediction", "probability").first()
    return {
        "prediction": "toxique" if res["prediction"] == 1.0 else "comestible",
        "probabilite_toxique": round(float(res["probability"][1]), 4),
    }