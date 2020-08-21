import React, { Suspense, useState } from "react";
import { useResource, useFetcher } from "rest-hooks";
import {
  AnnotationLayerResource,
  AnnotationExtractorResource,
  AnnotationClassResource,
} from "../../../resources";
import { AnnotationEntry } from "./AnnotationEntry";
import { useAlert } from "react-alert";
import useHotkeys from "react-use-hotkeys";

import * as _ from "lodash";

function ClassHeaderSelectTag(props: {
  classId: string;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
}) {
  const classInfo = useResource(AnnotationClassResource.detailShape(), {
    id: props.classId,
  });

  const shortcuts = classInfo.labels.reduce<{ [c: string]: string }>(
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
    // hooks in loop allowed because classInfo.labels is const.
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useHotkeys(c.toUpperCase(), () => props.onSelectTag(shortcuts[c]), []);
  }

  const highlightShortcut = (value: string) => {
    let result = [];
    let shortcut = _.findKey(shortcuts, (v) => v == value);

    for (let c of value) {
      if (c == shortcut) {
        shortcut = null;

        result.push(<b key={c}>[{c}]</b>);
      } else {
        result.push(c);
      }
    }

    return result;
  };

  return (
    <div
      style={{
        textAlign: "start",
        padding: 10,
      }}
    >
      <nav>
        {classInfo.labels.map((value: string, index: number) => {
          return (
            <button
              key={"label-" + value}
              onClick={() => props.onSelectTag(value)}
              disabled={props.selectedTag === value}
            >
              {highlightShortcut(value)}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function ClassHeaderCreateLayer(props: {
  paperId: string;
  classId: string;
  onNewLayer: (_: string) => void;
}) {
  const resourceId = { paperId: props.paperId };
  const alert = useAlert();

  const extractorList = useResource(AnnotationExtractorResource.listShape(), {
    classId: props.classId,
  });

  const createAnnotationLayerREST = useFetcher(AnnotationLayerResource.createShape());

  const createAnnotationLayer = async (name: string, from?: string) => {
    let result = await createAnnotationLayerREST(
      resourceId,
      {
        class: props.classId,
        training: false,
        from,
        name,
      } as any,
      [
        [
          AnnotationLayerResource.listShape(),
          resourceId,
          (newAnnotation: string, currentAnnotations: string[] | undefined) => {
            // announce newly created layer.
            props.onNewLayer(newAnnotation);

            return [...(currentAnnotations || []), newAnnotation];
          },
        ],
      ]
    );
  };

  return (
    <>
      <button onClick={() => createAnnotationLayer("Untitled")}>+layer</button>
      {extractorList.filter((e) => !e.trainable || e.trained).length > 0 && (
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
          <option value="">+from model</option>
          {extractorList.map((ex) => (
            <option key={ex.id} value={ex.id}>
              {ex.id}
            </option>
          ))}
        </select>
      )}
    </>
  );
}

function MenuModelHeader(props: {
  classId: string;
  paperId: string;
  color: boolean;
  selectedLayer: boolean;
  onSelectTag: (_: string) => void;
  selectedTag?: string;
  onNewLayer: (_: string) => void;
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
        <ClassHeaderCreateLayer {...props} />
        <div style={{ flex: 1 }}>{props.classId}</div>
      </h2>
    </>
  );
}

export function AnnotationClass(props: {
  paperId: string;
  classId: string;
  annotations: AnnotationLayerResource[];
  display: { [k: string]: boolean };
  onDisplayChange: (id: string, value: boolean) => void;
  selectedLayer?: string;
  onSelectLayer: (_?: string) => void;
  selectedTag?: string;
  onSelectTag: (_: string) => void;
  color: boolean;
}) {
  const selectedLayer = props.annotations
    .map((x) => x.id)
    .includes(props.selectedLayer);

  const [newLayer, setNewLayer] = useState<null | string>(null);

  const onNewLayer = (id: string) => {
    props.onDisplayChange(id, true);
    setNewLayer(id);
  };

  return (
    <div
      key={"annot_" + props.classId}
      style={{
        margin: "10px 0 10px 0",
        borderBottom: "solid gray 1px",
        backgroundColor: "#eaeaea",
      }}
    >
      <MenuModelHeader
        {...props}
        selectedLayer={selectedLayer}
        onNewLayer={onNewLayer}
      />
      <Suspense fallback={<div>Loading..</div>}>
        {props.annotations.map((layer) => (
          <AnnotationEntry
            key={layer.id}
            layer={layer.id}
            id={props.paperId}
            selected={props.selectedLayer === layer.id}
            new={newLayer === layer.id}
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
      {selectedLayer && <ClassHeaderSelectTag {...props} />}
    </div>
  );
}