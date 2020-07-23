import { Resource, AbstractInstanceType, MutateShape, SchemaDetail } from "rest-hooks";

export type AnnotationEnum = "none" | "pre_annot" | "pending" | "annot";
type AnnotationStatus = {
  status: AnnotationEnum;
};

export class PaperResource extends Resource {
  readonly id: string = "";
  readonly pdf: string = "";
  readonly layerStatus: {[key: string]: {count: number, training: boolean}} = {};

  pk() {
    return this.id;
  }

  static urlRoot = "http://localhost:8000/papers/";
}

export class ModelResource extends Resource {
  readonly id: string = "";
  readonly schema: {
    properties: {
      label: { type: "string"; enum: string[]; enumNames: string[] };
    };
  } = {} as any;

  pk() {
    return this.id;
  }

  static urlRoot = "http://localhost:8000/layers/";
}

export class LayerResource extends Resource {
  readonly id: string = "";
  readonly paperId: string = "";
  readonly kind: string = "";
  readonly name: string = "";
  readonly training: boolean = false;

  pk() {
    return this.paperId + "-" + this.id;
  }

  static get key() {
    return "LayerResource";
  }

  /**
   * Get the url for a Resource
   */
  static url<T extends typeof Resource>(
    this: T,
    urlParams: { paperId: string; id: string } & Partial<
      AbstractInstanceType<T>
    >
  ): string {
    if (urlParams) {
      if (this.pk(urlParams) !== undefined) {
        return `http://localhost:8000/papers/${urlParams.paperId}/layers/${urlParams.id}`;
      }
    }
    // since we're overriding the url() function we must keep the type the
    // same, which means we might not get urlParams
    throw new Error("Layers require paperId to retrieve");
  }

  /**
   * Get the url for many Resources
   */
  static listUrl(searchParams: { paperId: string }): string {
    if (searchParams && Object.keys(searchParams).length) {
      const { paperId, ...realSearchParams } = searchParams;
      const params = new URLSearchParams(realSearchParams as any);
      // this is essential for consistent url strings
      params.sort();
      return `http://localhost:8000/papers/${paperId}/layers/?${params.toString()}`;
    }
    throw new Error("Layers require paperId to retrieve");
  }
}

export class AnnotationResource extends Resource {
  readonly id: string = "";
  readonly paperId: string = "";
  readonly layerId: string = "";

  readonly min_h: number = 0;
  readonly max_h: number = 0;
  readonly min_v: number = 0;
  readonly max_v: number = 0;
  readonly page_num: number = 0;
  readonly label: string = "";


  pk() {
    return this.paperId + "-" + this.layerId + "-" + this.id;
  }

  static get key() {
    return "AnnotationResource";
  }

  /**
   * Get the url for a Resource
   */
  static url<T extends typeof Resource>(
    this: T,
    urlParams: { paperId: string; layerId: string, id: string } & Partial<
      AbstractInstanceType<T>
    >
  ): string {
    if (urlParams) {
      if (this.pk(urlParams) !== undefined) {
        return `http://localhost:8000/papers/${urlParams.paperId}/layers/${urlParams.layerId}/bbx/${urlParams.id}`;
      }
    }
    // since we're overriding the url() function we must keep the type the
    // same, which means we might not get urlParams
    throw new Error("Layers require paperId and layerId to retrieve");
  }

  /**
   * Get the url for many Resources
   */
  static listUrl(searchParams: { paperId: string, layerId: string }): string {
    if (searchParams && Object.keys(searchParams).length) {
      const { paperId, layerId, ...realSearchParams } = searchParams;
      const params = new URLSearchParams(realSearchParams as any);
      // this is essential for consistent url strings
      params.sort();
      return `http://localhost:8000/papers/${paperId}/layers/${layerId}/bbx/?${params.toString()}`;
    }
    throw new Error("Layers require paperId and layerId to retrieve");
  }

  static updateShape<T extends typeof Resource>(this: T): MutateShape<SchemaDetail<Readonly<AbstractInstanceType<T>>>,
  Readonly<object>,
  Partial<AbstractInstanceType<T>>
  > {
    return {
      ...super.updateShape(),
      options: {
        ...this.getFetchOptions(),
        optimisticUpdate: (params: any, body: any) => ({
          id: params.id,
          ...body
        })
      }
    }
  }

}