from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import RunOptions, SolveRequest
from .errors import register_exception_handlers
from .demo_adapter import run_quantum_solve, load_sample_problem
from .visualization import build_visualization


def create_app() -> FastAPI:
    app = FastAPI(
        title="Quantum Hackathon Backend Service",
        description="FastAPI wrapper for quantum optimization demo pipeline. All solves are local simulations.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.add_api_route("/health", health, methods=["GET"])
    app.add_api_route("/api/quantum/sample-problem", get_sample_problem, methods=["GET"])
    app.add_api_route("/api/quantum/solve", solve_quantum, methods=["POST"])
    return app


async def health():
    return {"status": "ok", "service": "backend_service"}


async def get_sample_problem():
    problem = load_sample_problem()
    return {"ok": True, "problem": problem}


async def solve_quantum(request: SolveRequest):
    raw_result = run_quantum_solve(request.problem, request.run_options)
    visualization = build_visualization(request.problem, raw_result)
    return {"ok": True, "raw_result": raw_result, "visualization": visualization}


app = create_app()
