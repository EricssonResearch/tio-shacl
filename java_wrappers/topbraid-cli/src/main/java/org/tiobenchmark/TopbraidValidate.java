package org.tiobenchmark;

import java.io.File;
import java.io.FileInputStream;
import java.io.StringWriter;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.StmtIterator;
import org.topbraid.shacl.validation.ValidationUtil;
import org.topbraid.shacl.vocabulary.SH;

/**
 * TopBraid SHACL validation CLI for tio-benchmark.
 *
 * Pre-loads data and shapes, then times ONLY the validation call.
 * Output: JSON to stdout: {"conforms":true/false,"violations":N,"validation_ms":...}
 */
public class TopbraidValidate {

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java -jar topbraid-shacl-cli.jar <data.ttl> <shapes.ttl>");
            System.exit(1);
        }

        String dataPath = args[0];
        String shapesPath = args[1];

        try {
            // Pre-load data and shapes (NOT timed — excludes I/O from measurement)
            Model dataModel = ModelFactory.createDefaultModel();
            try (FileInputStream fis = new FileInputStream(new File(dataPath))) {
                dataModel.read(fis, null, "TURTLE");
            }

            Model shapesModel = ModelFactory.createDefaultModel();
            try (FileInputStream fis = new FileInputStream(new File(shapesPath))) {
                shapesModel.read(fis, null, "TURTLE");
            }

            // Time ONLY the validation (validateShapes=false — match native CLI behavior)
            long t0 = System.nanoTime();
            Resource report = ValidationUtil.validateModel(dataModel, shapesModel, false);
            long elapsed = System.nanoTime() - t0;
            double validationMs = elapsed / 1_000_000.0;

            // Extract results from report
            boolean conforms = true;
            if (report.hasProperty(SH.conforms)) {
                conforms = report.getProperty(SH.conforms).getBoolean();
            }

            int violations = 0;
            Model reportModel = report.getModel();
            StmtIterator it = reportModel.listStatements(null,
                reportModel.createProperty("http://www.w3.org/ns/shacl#resultSeverity"),
                (org.apache.jena.rdf.model.RDFNode) null);
            while (it.hasNext()) {
                it.next();
                violations++;
            }

            // Serialize full SHACL report to Turtle
            StringWriter reportWriter = new StringWriter();
            reportModel.write(reportWriter, "TURTLE");
            String reportTurtle = reportWriter.toString()
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");

            System.out.printf(
                "{\"conforms\":%s,\"violations\":%d,\"validation_ms\":%.2f,\"report\":\"%s\"}%n",
                conforms, violations, validationMs, reportTurtle
            );

        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.getClass().getName();
            System.out.printf(
                "{\"conforms\":false,\"violations\":-1,\"validation_ms\":0,\"error\":\"%s\"}%n",
                msg.replace("\"", "\\\"").replace("\n", " ")
            );
            System.exit(1);
        }
    }
}
