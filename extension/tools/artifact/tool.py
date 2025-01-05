from __future__ import annotations
from griptape.artifacts import ErrorArtifact, BaseArtifact
from griptape.tools import BaseTool
from griptape.utils.decorators import activity
from schema import Schema, Literal
from attr import define, field


@define
class VisualizationTool(BaseTool):
    """Tool for generating visual artifacts from search results using React."""

    @activity(
        config={
            "description": "Creates a visual representation of information using React components. Best used for visualizing search results, comparisons, relationships, and structured data.",
            "schema": Schema(
                {
                    Literal(
                        "data",
                        description="The data to visualize - can be search results, competitor analysis, etc.",
                    ): str,
                    Literal(
                        "visualization_type",
                        description="Type of visualization to create: 'comparison', 'network', 'list', 'cards', 'timeline'",
                    ): str,
                }
            ),
        }
    )
    def create_visualization(self, params: dict) -> str:
        """Creates a React-based visualization artifact."""
        try:
            data = params["values"]["data"]
            viz_type = params["values"]["visualization_type"]

            # Create appropriate React component based on visualization type
            if viz_type == "comparison":
                return self._create_comparison_artifact(data)
            elif viz_type == "network":
                return self._create_network_artifact(data)
            elif viz_type == "cards":
                return self._create_cards_artifact(data)
            else:
                return self._create_generic_artifact(data)

        except Exception as e:
            return f"Failed to create visualization: {str(e)}"

    def _create_comparison_artifact(self, data: str) -> str:
        """Creates a comparison visualization."""
        return """
        import React from 'react';
        
        const ComparisonView = () => {
          const data = ${data}
          
          return (
            <div className="w-full p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.map((item, index) => (
                  <div key={index} className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-bold mb-2">{item.name}</h3>
                    <div className="space-y-2">
                      {Object.entries(item.features).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-600">{key}</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        };

        export default ComparisonView;
        """

    def _create_network_artifact(self, data: str) -> str:
        """Creates a network visualization."""
        return """
        import React from 'react';
        import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
        
        const NetworkView = () => {
          const data = ${data}
          
          return (
            <div className="w-full p-4">
              <LineChart width={600} height={400} data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />
              </LineChart>
            </div>
          );
        };
        
        export default NetworkView;
        """

    def _create_cards_artifact(self, data: str) -> str:
        """Creates a card-based visualization."""
        return """
        import React from 'react';
        
        const CardsView = () => {
          const data = ${data}
          
          return (
            <div className="w-full p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.map((item, index) => (
                  <div key={index} className="bg-white rounded-lg shadow-lg overflow-hidden">
                    <div className="p-6">
                      <h3 className="text-xl font-bold mb-2">{item.name}</h3>
                      <p className="text-gray-600">{item.description}</p>
                      {item.url && (
                        <a 
                          href={item.url}
                          className="mt-4 inline-block text-blue-600 hover:text-blue-800"
                        >
                          Learn More →
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        };
        
        export default CardsView;
        """
