# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=3.11
ARG VARIANT=""

# build stage
FROM python:${PYTHON_IMAGE}${VARIANT} AS build-stage

RUN pip install pipx

COPY . /project/
WORKDIR /project

RUN mkdir __pypackages__ && \
    python -m pipx run --no-cache pdm sync --prod --no-editable \


FROM python:${PYTHON_IMAGE}${VARIANT}

ARG PYTHON_IMAGE

ENV PYTHONPATH=/opt/entari-cli/pkgs

COPY --from=build-stage /project/__pypackages__/${PYTHON_IMAGE}/lib /opt/entari-cli/pkgs
COPY --from=build-stage /project/__pypackages__/${PYTHON_IMAGE}/bin/* /bin/

WORKDIR /workspaces

ENTRYPOINT ["entari"]
