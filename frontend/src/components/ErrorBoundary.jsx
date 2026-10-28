import { Component } from "react";

/** Prevents a crash (e.g. WebGL not available) from blanking the whole page. */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-box">
          <strong>{this.props.title || "This part of the page could not be displayed."}</strong>
          <div>{String(this.state.error.message || this.state.error)}</div>
          <div className="muted">{this.props.hint}</div>
        </div>
      );
    }
    return this.props.children;
  }
}
