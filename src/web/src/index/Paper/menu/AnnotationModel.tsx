import React, { Suspense } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  LayerResource,
  ExtractorResource,
  ModelResource,
} from "../../../resources";
import { AnnotationEntry } from "./AnnotationEntry";
import { useAlert } from "react-alert";
import useHotkeys from "react-use-hotkeys";

function ModelHeaderSelectTag(props: {
  selectedLayer: boolean;
  model_id: string;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
}) {
  const model_api = useResource(ModelResource.detailShape(), {
    id: props.model_id,
  });

  const shortcuts = model_api.labels.reduce<{ [c: string]: string }>(
    (sc, label) => {
      for (let c of label) {
        if (!(c in sc)) {
          return { ...sc, [c]: label };
        }
      }
      console.log("Warning: unable to deduce shortcut for ", label);
      return sc;
    },
    {}
  );

  for (let c in shortcuts) {
    // hooks in loop allowed because model_api.labels is const.
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useHotkeys(
      c.toUpperCase(),
      () => {
        if (props.selectedLayer) {
          props.onSelectTag(shortcuts[c]);
        }
      },
      []
    );
  }

  return (
    <div
      style={{
        textAlign: "start",
        padding: 10,
      }}
    >
      <div>Set label to:</div>
      <nav>
        {model_api.labels.map((value: string, index: number) => {
          return (
            <button
              key={"label-" + value}
              onClick={() => props.onSelectTag(value)}
              disabled={props.selectedTag === value}
            >
              {value}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function ModelHeaderCreateLayer(props: {
  model_id: string;
  paper_id: string;
  onDisplayChange: (id: string, value: boolean) => void;
}) {
  const resource_id = { paperId: props.paper_id };
  const alert = useAlert();

  const extractors_list = useResource(ExtractorResource.listShape(), {
    layer_id: props.model_id,
  });

  const createAnnotationLayerREST = useFetcher(LayerResource.createShape());

  const createAnnotationLayer = async (name: string, from?: string) => {
    console.log(resource_id);
    let result = await createAnnotationLayerREST(
      resource_id,
      {
        kind: props.model_id,
        training: false,
        from,
        name,
      } as any,
      [
        [
          LayerResource.listShape(),
          resource_id,
          (newAnnotation: string, currentAnnotations: string[] | undefined) => [
            ...(currentAnnotations || []),
            newAnnotation,
          ],
        ],
      ]
    );
    // display newly created layer.
    props.onDisplayChange(result.id, true);
  };


  return (
    <>
      <button onClick={() => createAnnotationLayer("Untitled")}>+new</button>
      <select
        onChange={async (e: React.ChangeEvent<HTMLSelectElement>) => {
          let target = e.target;
          if (target.value !== "") {
            target.disabled = true;
            await createAnnotationLayer(
              "from." + target.value,
              target.value
            ).catch(async (e) => {
              // errors are untyped we assume it's a network error.
              let error = await e.response.json();
              alert.error(error.message);
            });
            target.disabled = false;
            target.value = "";
          }
        }}
      >
        <option value="">apply model</option>
        {extractors_list.map((ex) => (
          <option key={ex.id} value={ex.id}>
            {ex.id}
          </option>
        ))}
      </select>
    </>
  );
}

function MenuModelHeader(props: {
  model_id: string;
  paper_id: string;
  onDisplayChange: (id: string, value: boolean) => void;
  color: boolean;
  selectedLayer: boolean;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
}) {

  return (
    <>
      <h2
        style={{
          fontVariant: "small-caps",
          backgroundColor: props.color ? "#fdd" : "white",
          padding: 10,
          display: "flex",
          flexDirection: "row",
          marginBottom: 4,
        }}
      >
        <ModelHeaderCreateLayer {...props}/>
        <div style={{ flex: 1 }}>{props.model_id}</div>
      </h2>
      <ModelHeaderSelectTag {...props} />
    </>
  );
}

export function AnnotationModel(props: {
  paper_id: string;
  model_id: string;
  annotations: LayerResource[];
  display: { [k: string]: boolean };
  onDisplayChange: (id: string, value: boolean) => void;
  selectedLayer?: string;
  onSelectLayer: (_?: string) => void;
  selectedTag?: string;
  onSelectTag: (_: string) => void;
  color: boolean;
}) {
  return (
    <div
      key={"annot_" + props.model_id}
      style={{
        margin: "10px 0 10px 0",
        borderBottom: "solid gray 1px",
        backgroundColor: "#eaeaea",
      }}
    >
      <MenuModelHeader
        {...props}
        selectedLayer={props.annotations
          .map((x) => x.id)
          .includes(props.selectedLayer)}
      />
      <Suspense fallback={<div>Loading..</div>}>
        {props.annotations.map((layer) => (
          <AnnotationEntry
            key={layer.id}
            layer={layer.id}
            id={props.paper_id}
            selected={props.selectedLayer === layer.id}
            onSelect={(v: boolean) => {
              if (v) {
                props.onSelectLayer(layer.id);
              } else {
                props.onSelectLayer(undefined);
              }
            }}
            display={props.display[layer.id]}
            onDisplayChange={(value: boolean) => {
              props.onDisplayChange(layer.id, value);
            }}
          />
        ))}
      </Suspense>
    </div>
  );
}
