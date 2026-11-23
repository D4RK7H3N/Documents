/**
 * Error boundary around the glb loading path: if a model file is missing
 * or malformed, fall back to the procedural species builder.
 */
import { Component } from "react";

export default class ModelLoadErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    this.props.onError?.(error);
  }

  render() {
    if (this.state.failed) return this.props.fallback ?? null;
    return this.props.children;
  }
}
