from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union
import time

import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import DATA_PATH, SQL_ENGINE, ENABLE_TENSORFLOW
from .misc.namespaces import *
from .classes import ALL_CLASSES, AnnotationClass, SegmentationAnnotationClass
from .paper import Paper, AnnotationLayerInfo, AnnotationLayerTag, association_table

from .extractors import Extractor
from .extractors.misc.features import FeatureExtractor
from .extractors.misc.aggreement import AgreementExtractor
from .extractors.crf import CRFExtractor
from .extractors.results import ResultsLatexExtractor, ResultsNaiveExtractor

if ENABLE_TENSORFLOW:
    from .extractors.cnn import CNNExtractor
    from .extractors.cnn1d import CNN1DExtractor


class TheoremKB:

    prefix: str
    classes: Dict[str, AnnotationClass]
    extractors: Dict[str, Extractor]

    def __init__(self, prefix=DATA_PATH) -> None:
        self.prefix = prefix

        self.classes = {}
        for l in ALL_CLASSES:
            self.classes[l.name] = l

        extractors = []

        extractors.append(FeatureExtractor("TextLine"))
        extractors.append(FeatureExtractor("String"))
        extractors.append(FeatureExtractor("TextBlock"))
        extractors.append(AgreementExtractor())
        extractors.append(ResultsLatexExtractor())
        extractors.append(ResultsNaiveExtractor())

        for l in ALL_CLASSES:
            if len(l.labels) == 0:
                continue

            extractors.append(CRFExtractor(prefix, name="line", class_=l, target=f"{ALTO}TextLine"))
            extractors.append(CRFExtractor(prefix, name="str", class_=l, target=f"{ALTO}String"))

            if ENABLE_TENSORFLOW:
                extractors.append(CNNExtractor(prefix, name="", class_=l))
                extractors.append(CNN1DExtractor(prefix, name="", class_=l))

        self.extractors = {}
        for e in extractors:
            self.extractors[f"{e.class_.name}.{e.name}"] = e

    def get_paper(self, session: Session, id: str) -> Paper:
        try:
            return session.query(Paper).get(id)
        except Exception:
            raise Exception("PaperNotFound")

    def get_layer(self, session: Session, id: str) -> AnnotationLayerInfo:
        try:
            return session.query(AnnotationLayerInfo).get(id)
        except Exception:
            raise Exception("LayerNotFound")

    def list_papers(
        self,
        session: Session,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        search: Optional[List[Tuple[str, str]]] = None,
        order_by_asc: Optional[Tuple[str, bool]] = None,
        count: bool = False,
    ) -> List[Paper]:
        req = session.query(Paper)

        valid_ann_layers = []

        if search is not None:
            for field, value in search:
                if field == "Paper.title":
                    req = req.filter(Paper.title.ilike(f"%%{value}%%"))
                elif field.startswith("Paper.layers.tag"):
                    valid_ann_layers.append(value)

        if len(valid_ann_layers) > 0:
            valid_tags = (
                session.query(AnnotationLayerTag)
                .filter(AnnotationLayerTag.id.in_(valid_ann_layers))
                .subquery()
            )

            valid_layers = (
                session.query(AnnotationLayerInfo)
                .join(valid_tags, AnnotationLayerInfo.tags)
                .subquery()
            )

            req = req.join(valid_layers)

        if order_by_asc is not None:
            order_by, asc = order_by_asc
            prop = None
            if order_by == "Paper.title":
                prop = Paper.title
            elif order_by == "Paper.id":
                prop = Paper.id

            if prop is not None:
                if asc:
                    req = req.order_by(prop.asc())
                else:
                    req = req.order_by(prop.desc())

        if count:
            return req.count()
        else:
            if offset is not None:
                req = req.offset(offset)
            if limit is not None:
                req = req.limit(limit)
            return req.all()

    def list_layer_tags(self, session: Session) -> List[AnnotationLayerTag]:
        return session.query(AnnotationLayerTag).all()

    def count_layer_tags(
        self, session: Session
    ) -> Dict[str, Tuple[AnnotationLayerTag, Dict[str, int]]]:

        tags_with_counts = (
            session.query(AnnotationLayerTag, AnnotationLayerInfo.class_, func.count())
            .join(AnnotationLayerTag, AnnotationLayerInfo.tags)
            .group_by(AnnotationLayerInfo.class_, AnnotationLayerTag.id)
        )

        res = {t.id: (t, {}) for t in session.query(AnnotationLayerTag).all()}

        for (tag, class_, count) in tags_with_counts:
            res[tag.id][1][class_] = count

        return res

    def get_layer_tag(self, session: Session, tag_id: str):
        return session.query(AnnotationLayerTag).get(tag_id)

    def add_layer_tag(
        self,
        session: Session,
        id: str,
        name: str,
        readonly: bool,
        data: dict,
    ):
        new_tag = AnnotationLayerTag(
            id=id,
            name=name,
            readonly=readonly,
            data_str=json.dumps(data),
        )

        session.add(new_tag)

        return new_tag

    def add_paper(self, session: Session, id: str, pdf_path: str):
        session.add(Paper(id=id, pdf_path=pdf_path))

    def delete_paper(self, session: Session, id: str):
        paper = session.query(Paper).get(id)
        session.delete(paper)
